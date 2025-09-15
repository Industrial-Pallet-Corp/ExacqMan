"""
ExacqMan Web Server - FastAPI Application

A web interface for the ExacqMan video processing tool that provides REST API endpoints
for video extraction, compression, and timelapse operations.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
import json
import logging
from datetime import datetime

from api.routes import router
from services.exacqman_service import ExacqManService
from services.file_service import FileService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ExacqMan Web API",
    description="Web interface for ExacqMan video processing tool",
    version="1.0.0"
)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving processed videos
app.mount("/exports", StaticFiles(directory="exports"), name="exports")

# Include API routes
app.include_router(router, prefix="/api")

# Initialize services
exacqman_service = ExacqManService()
file_service = FileService()

# Global job tracking (in production, use Redis or database)
active_jobs: Dict[str, Dict[str, Any]] = {}

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    logger.info("Starting ExacqMan Web Server...")
    
    # Ensure exports directory exists
    os.makedirs("exports", exist_ok=True)
    
    logger.info("ExacqMan Web Server started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Shutting down ExacqMan Web Server...")

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "ExacqMan Web API",
        "version": "1.0.0",
        "endpoints": {
            "extract": "/api/extract",
            "status": "/api/status/{job_id}",
            "files": "/api/files",
            "download": "/api/download/{filename}",
            "config": "/api/config/{config_file}",
            "cameras": "/api/cameras/{config_file}"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
