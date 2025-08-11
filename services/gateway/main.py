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

app = FastAPI(title="Gateway Service")

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "PROJECT_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
API_SERVICE_URL = os.getenv("API_SERVICE_URL", "http://localhost:8081")
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8082")
CLERK_JWKS_URL = os.getenv(
    "CLERK_JWKS_URL",
    "https://clerk.PROJECT_NAME.radicalsymmetry.com/.well-known/jwks.json",
)
TEST_BYPASS_TOKEN = os.getenv("TEST_BYPASS_TOKEN", "")

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
    return {"status": "healthy", "service": "gateway"}


@app.api_route(
    "/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
)
async def proxy_to_api(path: str, request: Request, user=Depends(verify_token)):
    """Proxy requests to API service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Prepare headers - remove host header and add user info
        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in ["host", "authorization"]
        }
        headers["X-User-Id"] = user.get("user_id", "")
        headers["X-User-Email"] = user.get("email", "")

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
        if "application/json" in content_type:
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type="application/json",
            )
        else:
            # For file downloads or other content types
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
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

        # Return response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type", "application/json"),
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
