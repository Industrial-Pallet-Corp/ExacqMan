"""
API Routes for ExacqMan Web Server

Defines REST API endpoints for video processing operations.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import Optional, List, Dict, Any
import uuid
import asyncio
import logging
from datetime import datetime
import os

from api.models import (
    ExtractRequest, CompressRequest, TimelapseRequest,
    JobStatus, FileInfo, ApiResponse
)
from services.exacqman_service import ExacqManService
from services.file_service import FileService

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
exacqman_service = ExacqManService()
file_service = FileService()

# Global job tracking (in production, use Redis or database)
active_jobs: Dict[str, Dict[str, Any]] = {}

@router.post("/extract", response_model=ApiResponse)
async def extract_video(
    request: ExtractRequest,
    background_tasks: BackgroundTasks
) -> ApiResponse:
    """
    Extract video from Exacqvision server with timelapse and compression.
    
    Args:
        request: ExtractRequest containing all necessary parameters
        background_tasks: FastAPI background tasks for async processing
        
    Returns:
        ApiResponse with job ID for tracking
    """
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Validate request
        if not request.camera_alias or not request.date or not request.start_time or not request.end_time:
            raise HTTPException(
                status_code=400,
                detail="Missing required parameters: camera_alias, date, start_time, end_time"
            )
        
        # Create job entry
        active_jobs[job_id] = {
            "status": "queued",
            "operation": "extract",
            "request": request.dict(),
            "created_at": datetime.now().isoformat(),
            "progress": 0,
            "message": "Job queued for processing"
        }
        
        # Start background task
        background_tasks.add_task(
            process_extract_job,
            job_id,
            request
        )
        
        logger.info(f"Extract job {job_id} queued for camera {request.camera_alias}")
        
        return ApiResponse(
            success=True,
            message="Extract job queued successfully",
            data={"job_id": job_id}
        )
        
    except Exception as e:
        logger.error(f"Error creating extract job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create extract job: {str(e)}")

@router.post("/compress", response_model=ApiResponse)
async def compress_video(
    request: CompressRequest,
    background_tasks: BackgroundTasks
) -> ApiResponse:
    """
    Compress an existing video file.
    
    Args:
        request: CompressRequest containing video file and quality settings
        background_tasks: FastAPI background tasks for async processing
        
    Returns:
        ApiResponse with job ID for tracking
    """
    try:
        job_id = str(uuid.uuid4())
        
        # Validate file exists
        if not os.path.exists(request.video_filename):
            raise HTTPException(
                status_code=404,
                detail=f"Video file not found: {request.video_filename}"
            )
        
        # Create job entry
        active_jobs[job_id] = {
            "status": "queued",
            "operation": "compress",
            "request": request.dict(),
            "created_at": datetime.now().isoformat(),
            "progress": 0,
            "message": "Job queued for processing"
        }
        
        # Start background task
        background_tasks.add_task(
            process_compress_job,
            job_id,
            request
        )
        
        logger.info(f"Compress job {job_id} queued for file {request.video_filename}")
        
        return ApiResponse(
            success=True,
            message="Compress job queued successfully",
            data={"job_id": job_id}
        )
        
    except Exception as e:
        logger.error(f"Error creating compress job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create compress job: {str(e)}")

@router.post("/timelapse", response_model=ApiResponse)
async def create_timelapse(
    request: TimelapseRequest,
    background_tasks: BackgroundTasks
) -> ApiResponse:
    """
    Create a timelapse from an existing video file.
    
    Args:
        request: TimelapseRequest containing video file and timelapse settings
        background_tasks: FastAPI background tasks for async processing
        
    Returns:
        ApiResponse with job ID for tracking
    """
    try:
        job_id = str(uuid.uuid4())
        
        # Validate file exists
        if not os.path.exists(request.video_filename):
            raise HTTPException(
                status_code=404,
                detail=f"Video file not found: {request.video_filename}"
            )
        
        # Create job entry
        active_jobs[job_id] = {
            "status": "queued",
            "operation": "timelapse",
            "request": request.dict(),
            "created_at": datetime.now().isoformat(),
            "progress": 0,
            "message": "Job queued for processing"
        }
        
        # Start background task
        background_tasks.add_task(
            process_timelapse_job,
            job_id,
            request
        )
        
        logger.info(f"Timelapse job {job_id} queued for file {request.video_filename}")
        
        return ApiResponse(
            success=True,
            message="Timelapse job queued successfully",
            data={"job_id": job_id}
        )
        
    except Exception as e:
        logger.error(f"Error creating timelapse job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create timelapse job: {str(e)}")

@router.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str) -> JobStatus:
    """
    Get the status of a processing job.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        JobStatus with current job information
    """
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = active_jobs[job_id]
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        message=job["message"],
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        result=job.get("result")
    )

@router.get("/files", response_model=List[FileInfo])
async def list_files() -> List[FileInfo]:
    """
    List all available video files in the exports directory.
    
    Returns:
        List of FileInfo objects for each file
    """
    try:
        files = file_service.list_video_files()
        return files
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download a processed video file.
    
    Args:
        filename: Name of the file to download
        
    Returns:
        FileResponse with the video file
    """
    try:
        file_path = file_service.get_file_path(filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="video/mp4"
        )
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a video file for processing.
    
    Args:
        file: Video file to upload
        
    Returns:
        ApiResponse with upload information
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only video files are allowed."
            )
        
        # Save uploaded file
        file_path = file_service.save_uploaded_file(file)
        
        logger.info(f"File uploaded successfully: {file_path}")
        
        return ApiResponse(
            success=True,
            message="File uploaded successfully",
            data={"filename": file.filename, "path": file_path}
        )
        
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

# Background task functions
async def process_extract_job(job_id: str, request: ExtractRequest):
    """Process an extract job in the background."""
    try:
        active_jobs[job_id]["status"] = "processing"
        active_jobs[job_id]["message"] = "Starting video extraction..."
        active_jobs[job_id]["progress"] = 10
        
        # Call ExacqMan service
        result = await exacqman_service.extract_video(request)
        
        active_jobs[job_id]["status"] = "completed"
        active_jobs[job_id]["progress"] = 100
        active_jobs[job_id]["message"] = "Video extraction completed successfully"
        active_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        active_jobs[job_id]["result"] = result
        
        logger.info(f"Extract job {job_id} completed successfully")
        
    except Exception as e:
        active_jobs[job_id]["status"] = "failed"
        active_jobs[job_id]["message"] = f"Extraction failed: {str(e)}"
        active_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
        logger.error(f"Extract job {job_id} failed: {str(e)}")

async def process_compress_job(job_id: str, request: CompressRequest):
    """Process a compress job in the background."""
    try:
        active_jobs[job_id]["status"] = "processing"
        active_jobs[job_id]["message"] = "Starting video compression..."
        active_jobs[job_id]["progress"] = 10
        
        # Call ExacqMan service
        result = await exacqman_service.compress_video(request)
        
        active_jobs[job_id]["status"] = "completed"
        active_jobs[job_id]["progress"] = 100
        active_jobs[job_id]["message"] = "Video compression completed successfully"
        active_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        active_jobs[job_id]["result"] = result
        
        logger.info(f"Compress job {job_id} completed successfully")
        
    except Exception as e:
        active_jobs[job_id]["status"] = "failed"
        active_jobs[job_id]["message"] = f"Compression failed: {str(e)}"
        active_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
        logger.error(f"Compress job {job_id} failed: {str(e)}")

async def process_timelapse_job(job_id: str, request: TimelapseRequest):
    """Process a timelapse job in the background."""
    try:
        active_jobs[job_id]["status"] = "processing"
        active_jobs[job_id]["message"] = "Starting timelapse creation..."
        active_jobs[job_id]["progress"] = 10
        
        # Call ExacqMan service
        result = await exacqman_service.create_timelapse(request)
        
        active_jobs[job_id]["status"] = "completed"
        active_jobs[job_id]["progress"] = 100
        active_jobs[job_id]["message"] = "Timelapse creation completed successfully"
        active_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        active_jobs[job_id]["result"] = result
        
        logger.info(f"Timelapse job {job_id} completed successfully")
        
    except Exception as e:
        active_jobs[job_id]["status"] = "failed"
        active_jobs[job_id]["message"] = f"Timelapse creation failed: {str(e)}"
        active_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
        logger.error(f"Timelapse job {job_id} failed: {str(e)}")
