"""
API Service - Core business logic and data operations
"""
import os
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import firestore, storage
from typing import Optional, Dict, Any
import json

app = FastAPI(title="API Service")

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "PROJECT_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", f"{PROJECT_ID}-uploads")

# Initialize GCP clients
db = None
storage_client = None

if ENVIRONMENT != "development":
    try:
        db = firestore.Client(project=PROJECT_ID)
        storage_client = storage.Client(project=PROJECT_ID)
    except Exception as e:
        print(f"Warning: Could not initialize GCP clients: {e}")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_user_from_headers(
    x_user_id: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None)
) -> Dict[str, str]:
    """Extract user info from headers set by gateway"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    return {
        "user_id": x_user_id,
        "email": x_user_email or ""
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "api",
        "project": PROJECT_ID,
        "environment": ENVIRONMENT,
        "status": "healthy"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "service": "api",
        "firestore": "connected" if db else "not connected",
        "storage": "connected" if storage_client else "not connected"
    }
    return health_status

@app.get("/users/me")
async def get_current_user(user = get_user_from_headers):
    """Get current user information"""
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "retrieved_at": datetime.utcnow().isoformat()
    }

@app.post("/items")
async def create_item(
    request: Request,
    user = get_user_from_headers
):
    """Create a new item in Firestore"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    data = await request.json()
    
    # Add metadata
    data["created_by"] = user["user_id"]
    data["created_at"] = datetime.utcnow().isoformat()
    data["updated_at"] = datetime.utcnow().isoformat()
    
    # Save to Firestore
    doc_ref = db.collection("items").document()
    doc_ref.set(data)
    
    return {
        "id": doc_ref.id,
        "message": "Item created successfully",
        **data
    }

@app.get("/items")
async def list_items(
    user = get_user_from_headers,
    limit: int = 10
):
    """List items for the current user"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Query items created by the user
    items_ref = db.collection("items")
    query = items_ref.where("created_by", "==", user["user_id"]).limit(limit)
    
    items = []
    for doc in query.stream():
        item_data = doc.to_dict()
        item_data["id"] = doc.id
        items.append(item_data)
    
    return {
        "items": items,
        "count": len(items),
        "user_id": user["user_id"]
    }

@app.get("/items/{item_id}")
async def get_item(
    item_id: str,
    user = get_user_from_headers
):
    """Get a specific item"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    doc_ref = db.collection("items").document(item_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item_data = doc.to_dict()
    
    # Check if user has access
    if item_data.get("created_by") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    item_data["id"] = doc.id
    return item_data

@app.put("/items/{item_id}")
async def update_item(
    item_id: str,
    request: Request,
    user = get_user_from_headers
):
    """Update an item"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    doc_ref = db.collection("items").document(item_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item_data = doc.to_dict()
    
    # Check if user has access
    if item_data.get("created_by") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update data
    update_data = await request.json()
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    doc_ref.update(update_data)
    
    return {
        "id": item_id,
        "message": "Item updated successfully",
        **update_data
    }

@app.delete("/items/{item_id}")
async def delete_item(
    item_id: str,
    user = get_user_from_headers
):
    """Delete an item"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    doc_ref = db.collection("items").document(item_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item_data = doc.to_dict()
    
    # Check if user has access
    if item_data.get("created_by") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    doc_ref.delete()
    
    return {"message": "Item deleted successfully", "id": item_id}

@app.post("/upload")
async def upload_file(
    request: Request,
    user = get_user_from_headers
):
    """Upload a file to Cloud Storage"""
    if not storage_client:
        raise HTTPException(status_code=503, detail="Storage not available")
    
    # This is a placeholder - actual implementation would handle file uploads
    return {
        "message": "File upload endpoint",
        "bucket": STORAGE_BUCKET,
        "user_id": user["user_id"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)