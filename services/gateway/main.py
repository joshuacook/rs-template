"""
Gateway Service - Public-facing authentication and routing service
"""
import os
import httpx
from fastapi import FastAPI, Request, HTTPException, Depends, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
import jwt
from jwt import PyJWKClient
import google.auth
import google.auth.transport.requests
import google.oauth2.id_token

app = FastAPI(title="Gateway Service")

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "PROJECT_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
API_SERVICE_URL = os.getenv("API_BASE_URL", os.getenv("API_SERVICE_URL", "http://localhost:8081"))
AI_SERVICE_URL = os.getenv("AI_BASE_URL", os.getenv("AI_SERVICE_URL", "http://localhost:8082"))
CLERK_JWKS_URL = os.getenv(
    "CLERK_JWKS_URL",
    "https://clerk.PROJECT_NAME.radicalsymmetry.com/.well-known/jwks.json",
)
TEST_BYPASS_TOKEN = os.getenv("TEST_BYPASS_TOKEN", "")

# Check if running in Cloud Run
IS_CLOUD_RUN = os.getenv("K_SERVICE") is not None

# Get authentication token for service-to-service calls
def get_auth_token(target_url: str) -> Optional[str]:
    """Get authentication token for calling Cloud Run services"""
    if not IS_CLOUD_RUN:
        return None
    
    try:
        # Get ID token for the target audience (service URL)
        auth_req = google.auth.transport.requests.Request()
        id_token = google.oauth2.id_token.fetch_id_token(auth_req, target_url)
        return id_token
    except Exception as e:
        print(f"Failed to get auth token for {target_url}: {e}")
        return None

# Log configuration on startup
print(f"Gateway Service starting...")
print(f"Environment: {ENVIRONMENT}")
print(f"Project ID: {PROJECT_ID}")
print(f"API Service URL: {API_SERVICE_URL}")
print(f"AI Service URL: {AI_SERVICE_URL}")
print(f"Is Cloud Run: {IS_CLOUD_RUN}")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize JWKS client for Clerk token validation
jwks_client = None
if ENVIRONMENT != "development":
    try:
        jwks_client = PyJWKClient(CLERK_JWKS_URL)
    except Exception as e:
        print(f"Warning: Could not initialize JWKS client: {e}")


def verify_token(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Verify JWT token from Clerk or use test bypass"""
    # Check authorization header format first
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format. Expected: Bearer <token>",
        )

    # Check for test bypass token
    print(f"DEBUG: TEST_BYPASS_TOKEN configured: {bool(TEST_BYPASS_TOKEN)}")
    print(f"DEBUG: TEST_BYPASS_TOKEN length: {len(TEST_BYPASS_TOKEN) if TEST_BYPASS_TOKEN else 0}")
    print(f"DEBUG: Auth header length: {len(authorization)}")
    print(f"DEBUG: Token match: {authorization == f'Bearer {TEST_BYPASS_TOKEN}'}")
    
    if TEST_BYPASS_TOKEN and authorization == f"Bearer {TEST_BYPASS_TOKEN}":
        # Return standardized test admin user
        return {
            "user_id": "test_admin_123",
            "email": "admin@test.example.com",
            "name": "Test Admin",
            "role": "admin",
        }

    # In development mode with no test token, allow a default dev user
    if ENVIRONMENT == "development" and not jwks_client:
        return {"user_id": "dev_user", "email": "dev@example.com"}

    # Verify real JWT token
    if not jwks_client:
        raise HTTPException(
            status_code=503, detail="Authentication service not configured"
        )

    try:
        token = authorization.replace("Bearer ", "")
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token, signing_key.key, algorithms=["RS256"], audience=PROJECT_ID
        )
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "gateway",
        "project": PROJECT_ID,
        "environment": ENVIRONMENT,
        "status": "healthy",
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "gateway",
        "version": os.getenv("VERSION", "1.0.0"),
        "environment": ENVIRONMENT
    }

@app.get("/debug/env")
async def debug_env():
    """Debug endpoint to check environment"""
    return {
        "environment": ENVIRONMENT,
        "test_bypass_token_configured": bool(TEST_BYPASS_TOKEN),
        "test_bypass_token_length": len(TEST_BYPASS_TOKEN) if TEST_BYPASS_TOKEN else 0,
        "clerk_jwks_url_configured": bool(CLERK_JWKS_URL),
        "jwks_configured": bool(jwks_client),
        "project_id": PROJECT_ID
    }


@app.api_route(
    "/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
)
async def proxy_to_api(path: str, request: Request, user=Depends(verify_token)):
    """Proxy requests to API service"""
    # Use longer timeout for file operations
    timeout = httpx.Timeout(60.0, connect=10.0) if "file" in path else httpx.Timeout(30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Prepare headers - remove host header and add user info
        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in ["host", "authorization"]
        }
        headers["X-User-Id"] = user.get("user_id", "")
        headers["X-User-Email"] = user.get("email", "")
        
        # Add authentication for Cloud Run
        auth_token = get_auth_token(API_SERVICE_URL)
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        # Handle query parameters
        query_params = str(request.url.query) if request.url.query else ""
        url = f"{API_SERVICE_URL}/{path}"
        if query_params:
            url = f"{url}?{query_params}"

        # Make the request
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=await request.body()
            if request.method in ["POST", "PUT", "PATCH"]
            else None,
        )

        # Return appropriate response type
        content_type = response.headers.get("content-type", "")
        
        # Get headers to forward (exclude hop-by-hop headers)
        headers_to_forward = {
            key: value
            for key, value in response.headers.items()
            if key.lower() not in ["content-encoding", "content-length", "transfer-encoding", "connection"]
        }
        
        if "application/json" in content_type:
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=headers_to_forward,
                media_type="application/json",
            )
        else:
            # For other content types
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=headers_to_forward,
                media_type=content_type,
            )


@app.api_route(
    "/ai/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
)
async def proxy_to_ai(path: str, request: Request, user=Depends(verify_token)):
    """Proxy requests to AI service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Prepare headers
        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in ["host", "authorization"]
        }
        headers["X-User-Id"] = user.get("user_id", "")
        
        # Add authentication for Cloud Run
        auth_token = get_auth_token(AI_SERVICE_URL)
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        # Handle query parameters
        query_params = str(request.url.query) if request.url.query else ""
        url = f"{AI_SERVICE_URL}/{path}"
        if query_params:
            url = f"{url}?{query_params}"

        # Make the request
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=await request.body()
            if request.method in ["POST", "PUT", "PATCH"]
            else None,
        )

        # Get headers to forward (exclude hop-by-hop headers)
        headers_to_forward = {
            key: value
            for key, value in response.headers.items()
            if key.lower() not in ["content-encoding", "content-length", "transfer-encoding", "connection"]
        }
        
        # Return response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=headers_to_forward,
            media_type=response.headers.get("content-type", "application/json"),
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
