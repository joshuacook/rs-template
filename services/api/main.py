"""
API Service - Core business logic and data operations
"""
import os
import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Header, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google.cloud import firestore, storage
from typing import Optional, Dict
import io

app = FastAPI(title="API Service")

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "PROJECT_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", f"{PROJECT_ID}-uploads")

# Initialize GCP clients
db = None
storage_client = None

try:
    db = firestore.Client(project=PROJECT_ID)
    storage_client = storage.Client(project=PROJECT_ID)
    print(f"Successfully connected to GCP project: {PROJECT_ID}")
except Exception as e:
    print(f"Warning: Could not initialize GCP clients: {e}")
    print("Running without GCP services - some features will be unavailable")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_user_from_headers(
    x_user_id: Optional[str] = Header(None), x_user_email: Optional[str] = Header(None)
) -> Dict[str, str]:
    """Extract user info from headers set by gateway"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    return {"user_id": x_user_id, "email": x_user_email or ""}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "api",
        "project": PROJECT_ID,
        "environment": ENVIRONMENT,
        "status": "healthy",
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "service": "api",
        "firestore": "connected" if db else "not connected",
        "storage": "connected" if storage_client else "not connected",
    }
    return health_status


@app.get("/users/me")
async def get_current_user(user: Dict = Depends(get_user_from_headers)):
    """Get current user information"""
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "retrieved_at": datetime.utcnow().isoformat(),
    }


@app.post("/items")
async def create_item(request: Request, user: Dict = Depends(get_user_from_headers)):
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

    return {"id": doc_ref.id, "message": "Item created successfully", **data}


@app.get("/items")
async def list_items(user: Dict = Depends(get_user_from_headers), limit: int = 10):
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

    return {"items": items, "count": len(items), "user_id": user["user_id"]}


@app.get("/items/{item_id}")
async def get_item(item_id: str, user: Dict = Depends(get_user_from_headers)):
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
    item_id: str, request: Request, user: Dict = Depends(get_user_from_headers)
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

    return {"id": item_id, "message": "Item updated successfully", **update_data}


@app.delete("/items/{item_id}")
async def delete_item(item_id: str, user: Dict = Depends(get_user_from_headers)):
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


@app.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...), user: Dict = Depends(get_user_from_headers)
):
    """Upload a file to Cloud Storage"""
    if not storage_client:
        raise HTTPException(status_code=503, detail="Storage not available")

    try:
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        file_path = f"uploads/{user['user_id']}/{file_id}/{file.filename}"

        # Get bucket
        bucket = storage_client.bucket(STORAGE_BUCKET)
        blob = bucket.blob(file_path)

        # Upload file
        contents = await file.read()
        blob.upload_from_string(contents, content_type=file.content_type)

        # Save metadata to Firestore if available
        if db:
            doc_ref = db.collection("files").document(file_id)
            doc_ref.set(
                {
                    "file_id": file_id,
                    "file_name": file.filename,
                    "file_path": file_path,
                    "content_type": file.content_type,
                    "size": len(contents),
                    "uploaded_by": user["user_id"],
                    "uploaded_at": datetime.utcnow().isoformat(),
                    "bucket": STORAGE_BUCKET,
                }
            )

        return {
            "file_id": file_id,
            "file_name": file.filename,
            "url": f"gs://{STORAGE_BUCKET}/{file_path}",
            "message": "File uploaded successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/files/{file_id}/download")
async def download_file(file_id: str, user: Dict = Depends(get_user_from_headers)):
    """Get a pre-signed URL for downloading a file from Cloud Storage"""
    if not storage_client:
        raise HTTPException(status_code=503, detail="Storage not available")

    try:
        # Get file metadata from Firestore
        if db:
            doc_ref = db.collection("files").document(file_id)
            doc = doc_ref.get()

            if not doc.exists:
                raise HTTPException(status_code=404, detail="File not found")

            file_data = doc.to_dict()

            # Check access
            if file_data.get("uploaded_by") != user["user_id"]:
                raise HTTPException(status_code=403, detail="Access denied")

            file_path = file_data["file_path"]
            file_name = file_data["file_name"]
            content_type = file_data.get("content_type", "application/octet-stream")
        else:
            # Fallback if Firestore not available
            file_path = f"uploads/{user['user_id']}/{file_id}/*"
            file_name = "download"
            content_type = "application/octet-stream"

        # Generate pre-signed URL using IAM SignBlob API
        import google.auth
        from google.auth import impersonated_credentials
        from datetime import timedelta
        
        # Get current service account email
        credentials, project = google.auth.default()
        _, service_account_email = google.auth.default()
        
        # Create impersonated credentials for signing
        signing_credentials = impersonated_credentials.Credentials(
            source_credentials=credentials,
            target_principal=f"api-service-staging@{PROJECT_ID}.iam.gserviceaccount.com",
            target_scopes=["https://www.googleapis.com/auth/devstorage.read_only"],
            lifetime=3600,
        )

        bucket = storage_client.bucket(STORAGE_BUCKET)
        blob = bucket.blob(file_path)

        if not blob.exists():
            raise HTTPException(status_code=404, detail="File not found in storage")

        # Generate a pre-signed URL valid for 1 hour using impersonated credentials
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="GET",
            response_disposition=f"attachment; filename={file_name}",
            response_type=content_type,
            credentials=signing_credentials
        )

        return {
            "download_url": url,
            "file_name": file_name,
            "content_type": content_type,
            "expires_in": 3600  # seconds
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@app.get("/files")
async def list_files(user: Dict = Depends(get_user_from_headers), limit: int = 10):
    """List files uploaded by the user"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Query files from Firestore
        files_ref = db.collection("files")
        query = files_ref.where("uploaded_by", "==", user["user_id"]).limit(limit)

        files = []
        for doc in query.stream():
            file_data = doc.to_dict()
            files.append(file_data)

        return {"files": files, "count": len(files), "user_id": user["user_id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@app.delete("/files/{file_id}")
async def delete_file(file_id: str, user: Dict = Depends(get_user_from_headers)):
    """Delete a file from Cloud Storage"""
    if not storage_client:
        raise HTTPException(status_code=503, detail="Storage not available")

    try:
        # Get file metadata from Firestore
        if db:
            doc_ref = db.collection("files").document(file_id)
            doc = doc_ref.get()

            if not doc.exists:
                raise HTTPException(status_code=404, detail="File not found")

            file_data = doc.to_dict()

            # Check access
            if file_data.get("uploaded_by") != user["user_id"]:
                raise HTTPException(status_code=403, detail="Access denied")

            file_path = file_data["file_path"]

            # Delete from storage
            bucket = storage_client.bucket(STORAGE_BUCKET)
            blob = bucket.blob(file_path)
            blob.delete()

            # Delete metadata from Firestore
            doc_ref.delete()
        else:
            raise HTTPException(status_code=503, detail="Database not available")

        return {"message": "File deleted successfully", "file_id": file_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@app.get("/files/{file_id}/signed-url")
async def get_signed_url(
    file_id: str, user: Dict = Depends(get_user_from_headers), expires_in: int = 3600
):
    """Generate a signed URL for direct file access"""
    if not storage_client:
        raise HTTPException(status_code=503, detail="Storage not available")

    try:
        # Get file metadata from Firestore
        if db:
            doc_ref = db.collection("files").document(file_id)
            doc = doc_ref.get()

            if not doc.exists:
                raise HTTPException(status_code=404, detail="File not found")

            file_data = doc.to_dict()

            # Check access
            if file_data.get("uploaded_by") != user["user_id"]:
                raise HTTPException(status_code=403, detail="Access denied")

            file_path = file_data["file_path"]
        else:
            raise HTTPException(status_code=503, detail="Database not available")

        # Generate signed URL
        bucket = storage_client.bucket(STORAGE_BUCKET)
        blob = bucket.blob(file_path)

        if not blob.exists():
            raise HTTPException(status_code=404, detail="File not found in storage")

        signed_url = blob.generate_signed_url(
            expiration=timedelta(seconds=expires_in), method="GET"
        )

        return {"signed_url": signed_url, "expires_in": expires_in, "file_id": file_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate signed URL: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
