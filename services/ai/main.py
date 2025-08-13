"""
AI Service - AI/LLM operations with LangChain and Langfuse tracing
"""
import os
from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from langfuse import Langfuse

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

app = FastAPI(title="AI Service")

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "PROJECT_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Model configuration
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
MODEL_NAME = os.getenv("MODEL_NAME", "")

# Provider-specific API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Langfuse configuration
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

# Initialize Langfuse client
langfuse_client = None
if LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY:
    try:
        langfuse_client = Langfuse(
            secret_key=LANGFUSE_SECRET_KEY,
            public_key=LANGFUSE_PUBLIC_KEY,
            host=LANGFUSE_HOST,
        )
    except Exception as e:
        print(f"Warning: Could not initialize Langfuse: {e}")

# Initialize LLM based on provider - fail loudly if misconfigured
llm = None
if not MODEL_PROVIDER or not MODEL_NAME:
    raise ValueError("MODEL_PROVIDER and MODEL_NAME must be set")

if MODEL_PROVIDER == "openai":
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY required for OpenAI provider")
    llm = ChatOpenAI(
        model=MODEL_NAME,
        api_key=OPENAI_API_KEY,
        temperature=0.7,
    )
elif MODEL_PROVIDER == "anthropic":
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY required for Anthropic provider")
    llm = ChatAnthropic(
        model=MODEL_NAME,
        api_key=ANTHROPIC_API_KEY,
        temperature=0.7,
    )
elif MODEL_PROVIDER == "google":
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY required for Google provider")
    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.7,
    )
else:
    raise ValueError(f"Unsupported MODEL_PROVIDER: {MODEL_PROVIDER}")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Log configuration on startup
print(f"AI Service starting...")
print(f"Environment: {ENVIRONMENT}")
print(f"Model Provider: {MODEL_PROVIDER}")
print(f"Model Name: {MODEL_NAME}")
print(f"OpenAI API Key configured: {'Yes' if OPENAI_API_KEY else 'No'}")
print(f"Anthropic API Key configured: {'Yes' if ANTHROPIC_API_KEY else 'No'}")
print(f"Google API Key configured: {'Yes' if GOOGLE_API_KEY else 'No'}")
print(f"Langfuse configured: {'Yes' if langfuse_client else 'No'}")


def get_user_from_headers(x_user_id: Optional[str] = Header(None)) -> str:
    """Extract user ID from headers set by gateway"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    return x_user_id


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ai",
        "project": PROJECT_ID,
        "environment": ENVIRONMENT,
        "status": "healthy",
        "provider": MODEL_PROVIDER,
        "model": MODEL_NAME,
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai",
        "provider": MODEL_PROVIDER,
        "model": MODEL_NAME,
        "langfuse": "configured" if langfuse_client else "not configured",
    }


@app.post("/chat")
async def chat_completion(
    request: Request, user_id: str = Depends(get_user_from_headers)
):
    """Chat completion endpoint"""
    if not llm:
        raise HTTPException(status_code=503, detail="LLM not configured")

    data = await request.json()
    messages = data.get("messages", [])
    max_tokens = data.get("max_tokens", data.get("max_completion_tokens", 1000))

    if not messages:
        raise HTTPException(status_code=400, detail="Messages are required")

    try:
        # Convert messages to LangChain format
        langchain_messages = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "user":
                langchain_messages.append(HumanMessage(content=content))
            # For assistant messages, we'll treat them as human messages with context
            # In production, you might want to handle this differently
            else:
                langchain_messages.append(HumanMessage(content=f"[Previous Assistant]: {content}"))

        # Create Langfuse trace if available
        trace = None
        if langfuse_client:
            trace = langfuse_client.trace(
                name="chat_completion",
                user_id=user_id,
                metadata={
                    "project": PROJECT_ID,
                    "environment": ENVIRONMENT,
                    "provider": MODEL_PROVIDER,
                    "model": MODEL_NAME,
                }
            )

        # Use LangChain's unified API - it handles provider differences automatically
        response = await llm.ainvoke(langchain_messages)

        # Extract content from response
        response_content = response.content if hasattr(response, 'content') else str(response)
        
        # Calculate token usage (approximation for non-OpenAI providers)
        # LangChain doesn't always provide token counts for all providers
        usage = {
            "prompt_tokens": sum(len(msg.content.split()) * 1.3 for msg in langchain_messages),  # Rough estimate
            "completion_tokens": len(response_content.split()) * 1.3,  # Rough estimate
            "total_tokens": 0
        }
        
        # Try to get actual usage if available
        if hasattr(response, 'response_metadata'):
            metadata = response.response_metadata
            if 'token_usage' in metadata:
                usage = metadata['token_usage']
            elif 'usage' in metadata:
                usage = metadata['usage']
        
        usage["total_tokens"] = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)

        # Log generation to Langfuse if available
        if trace:
            trace.generation(
                name="chat_completion",
                model=MODEL_NAME,
                input=messages,
                output=response_content,
                usage=usage,
                metadata={"provider": MODEL_PROVIDER}
            )

        return {
            "response": response_content,
            "model": MODEL_NAME,
            "provider": MODEL_PROVIDER,
            "usage": usage,
            "user_id": user_id,
        }

    except Exception as e:
        # Log error to Langfuse if available
        if langfuse_client:
            langfuse_client.trace(
                name="chat_completion_error",
                user_id=user_id,
                metadata={
                    "error": str(e),
                    "provider": MODEL_PROVIDER,
                    "model": MODEL_NAME,
                },
                level="error"
            )
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8082)