"""
AI Service - AI/LLM operations with OpenAI and Langfuse tracing
"""
import os
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List
from openai import OpenAI
from langfuse import Langfuse
from langfuse.openai import openai as langfuse_openai
import json

app = FastAPI(title="AI Service")

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "PROJECT_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

# Initialize clients
openai_client = None
langfuse_client = None

if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    
if LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY:
    try:
        langfuse_client = Langfuse(
            secret_key=LANGFUSE_SECRET_KEY,
            public_key=LANGFUSE_PUBLIC_KEY,
            host=LANGFUSE_HOST
        )
        # Patch OpenAI client for automatic tracing
        langfuse_openai.register(openai_client, langfuse_client)
    except Exception as e:
        print(f"Warning: Could not initialize Langfuse: {e}")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_user_from_headers(
    x_user_id: Optional[str] = Header(None)
) -> str:
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
        "model": OPENAI_MODEL
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai",
        "openai": "configured" if openai_client else "not configured",
        "langfuse": "configured" if langfuse_client else "not configured"
    }

@app.post("/chat")
async def chat_completion(
    request: Request,
    user_id: str = get_user_from_headers
):
    """Chat completion endpoint"""
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI client not configured")
    
    data = await request.json()
    messages = data.get("messages", [])
    temperature = data.get("temperature", 0.7)
    max_tokens = data.get("max_tokens", 1000)
    
    if not messages:
        raise HTTPException(status_code=400, detail="Messages are required")
    
    try:
        # Create trace in Langfuse
        trace = None
        if langfuse_client:
            trace = langfuse_client.trace(
                name="chat_completion",
                user_id=user_id,
                metadata={
                    "project": PROJECT_ID,
                    "environment": ENVIRONMENT
                }
            )
        
        # Call OpenAI
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Log to Langfuse
        if trace:
            trace.generation(
                name="chat_completion",
                model=OPENAI_MODEL,
                input=messages,
                output=response.choices[0].message.content,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            )
        
        return {
            "response": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "user_id": user_id
        }
        
    except Exception as e:
        # Log error to Langfuse
        if trace:
            trace.event(
                name="error",
                level="error",
                metadata={"error": str(e)}
            )
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze_text(
    request: Request,
    user_id: str = get_user_from_headers
):
    """Analyze text for insights"""
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI client not configured")
    
    data = await request.json()
    text = data.get("text", "")
    analysis_type = data.get("analysis_type", "summary")
    
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    # Define analysis prompts
    prompts = {
        "summary": "Provide a concise summary of the following text:",
        "sentiment": "Analyze the sentiment of the following text and categorize it as positive, negative, or neutral:",
        "key_points": "Extract the key points from the following text:",
        "action_items": "Identify any action items or tasks mentioned in the following text:"
    }
    
    prompt = prompts.get(analysis_type, prompts["summary"])
    
    try:
        # Create trace in Langfuse
        trace = None
        if langfuse_client:
            trace = langfuse_client.trace(
                name=f"analyze_{analysis_type}",
                user_id=user_id,
                metadata={
                    "project": PROJECT_ID,
                    "environment": ENVIRONMENT,
                    "analysis_type": analysis_type
                }
            )
        
        # Call OpenAI
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes text."},
                {"role": "user", "content": f"{prompt}\n\n{text}"}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        result = response.choices[0].message.content
        
        # Log to Langfuse
        if trace:
            trace.generation(
                name=f"analyze_{analysis_type}",
                model=OPENAI_MODEL,
                input={"text": text, "analysis_type": analysis_type},
                output=result,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            )
        
        return {
            "analysis_type": analysis_type,
            "result": result,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "user_id": user_id
        }
        
    except Exception as e:
        # Log error to Langfuse
        if trace:
            trace.event(
                name="error",
                level="error",
                metadata={"error": str(e)}
            )
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embeddings")
async def create_embeddings(
    request: Request,
    user_id: str = get_user_from_headers
):
    """Create embeddings for text"""
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI client not configured")
    
    data = await request.json()
    texts = data.get("texts", [])
    
    if not texts:
        raise HTTPException(status_code=400, detail="Texts are required")
    
    try:
        # Create embeddings
        response = openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=texts
        )
        
        embeddings = [item.embedding for item in response.data]
        
        # Log to Langfuse
        if langfuse_client:
            langfuse_client.trace(
                name="create_embeddings",
                user_id=user_id,
                metadata={
                    "project": PROJECT_ID,
                    "environment": ENVIRONMENT,
                    "num_texts": len(texts),
                    "model": "text-embedding-ada-002"
                }
            )
        
        return {
            "embeddings": embeddings,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "user_id": user_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)