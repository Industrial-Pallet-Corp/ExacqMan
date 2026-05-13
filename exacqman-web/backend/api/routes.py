"""
API Routes for ExacqMan Web Server

Defines REST API endpoints for video processing operations.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional, List, Dict, Any
import uuid
import asyncio
import logging
from datetime import datetime
import os

from api.models import (
    ExtractRequest, ProcessedVideo, CameraInfo, ConfigInfo,
    JobStatus, FileInfo, ApiResponse
)
from services.exacqman_service import ExacqManService
from services.file_service import FileService
from services.config_service import ConfigService

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
exacqman_service = ExacqManService()
file_service = FileService()
config_service = ConfigService()

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
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Validate camera exists in config
        if not config_service.validate_camera(request.config_file, request.camera_alias):
            raise HTTPException(
                status_code=400, 
                detail=f"Camera '{request.camera_alias}' not found in configuration"
            )
        
        # Add job to tracking
        active_jobs[job_id] = {
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "operation": "extract",
            "request": request.dict(),
            "progress": 0,
            "message": "Job queued for processing"
        }
        
        # Start extraction in background
        background_tasks.add_task(process_extract_job, job_id, request)
        
        logger.info(f"Extract job {job_id} queued for camera {request.camera_alias}")
        
        return ApiResponse(
            success=True,
            message="Extract job queued successfully",
            data={"job_id": job_id}
        )
        
    except Exception as e:
        logger.error(f"Error creating extract job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create extract job: {str(e)}")

@router.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str) -> JobStatus:
    """
    Get the status of a processing job.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        JobStatus object with current job information
    """
    try:
        logger.info(f"Getting status for job {job_id}")
        
        if job_id not in active_jobs:
            logger.warning(f"Job {job_id} not found in active_jobs")
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = active_jobs[job_id]
        logger.info(f"Job {job_id} status: {job.get('status', 'unknown')}")
        
        return JobStatus(
            job_id=job_id,
            status=job["status"],
            progress=job.get("progress", 0),
            message=job.get("message", ""),
            created_at=job["created_at"],
            completed_at=job.get("completed_at"),
            result=job.get("result")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")

@router.get("/files", response_model=List[FileInfo])
async def list_processed_videos() -> List[FileInfo]:
    """
    List all processed video files.
    
    Returns:
        List of FileInfo objects for processed videos
    """
    try:
        files = file_service.get_processed_videos()
        return files
        
    except Exception as e:
        logger.error(f"Error listing processed videos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@router.get("/download/{filename}")
async def download_video(filename: str):
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
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")

@router.get("/configs", response_model=List[str])
async def get_available_configs() -> List[str]:
    """
    Get list of available configuration files.
    
    Returns:
        List of configuration file names
    """
    try:
        config_files = config_service.get_available_config_files()
        return config_files
    except Exception as e:
        logger.error(f"Error getting available configs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get available configurations")

@router.get("/config/{config_file}", response_model=ConfigInfo)
async def get_config_info(config_file: str) -> ConfigInfo:
    """
    Get configuration information including available cameras and servers.
    
    Args:
        config_file: Path to the configuration file
        
    Returns:
        ConfigInfo with available cameras, servers, and options
    """
    try:
        config_info = config_service.get_config_info(config_file)
        return config_info
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Configuration file not found: {config_file}")
    except Exception as e:
        logger.error(f"Error getting config info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")

@router.get("/cameras/{config_file}", response_model=List[CameraInfo])
async def get_cameras(config_file: str) -> List[CameraInfo]:
    """
    Get list of available cameras from configuration file.
    
    Args:
        config_file: Path to the configuration file
        
    Returns:
        List of CameraInfo objects
    """
    try:
        cameras = config_service.get_available_cameras(config_file)
        return cameras
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Configuration file not found: {config_file}")
    except Exception as e:
        logger.error(f"Error getting cameras: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get cameras: {str(e)}")

@router.delete("/files/{filename}", response_model=ApiResponse)
async def delete_video(filename: str) -> ApiResponse:
    """
    Delete a processed video file.
    
    Args:
        filename: Name of the file to delete
        
    Returns:
        ApiResponse indicating success or failure
    """
    try:
        success = file_service.delete_file(filename)
        
        if success:
            return ApiResponse(
                success=True,
                message=f"File '{filename}' deleted successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete file")
            
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

# Background task functions

async def process_extract_job(job_id: str, request: ExtractRequest):
    """
    Process an extract job in the background with real-time progress tracking.
    
    Args:
        job_id: Unique job identifier
        request: ExtractRequest object
    """
    def update_progress(progress: int, message: str):
        """Update job progress in real-time."""
        if job_id in active_jobs:
            active_jobs[job_id]["progress"] = progress
            active_jobs[job_id]["message"] = message
            logger.info(f"Job {job_id}: {message} ({progress}%)")
    
    try:
        # Update job status
        active_jobs[job_id]["status"] = "processing"
        active_jobs[job_id]["message"] = "Starting video extraction..."
        active_jobs[job_id]["progress"] = 0
        
        # Run the extraction with progress tracking
        result = await exacqman_service.extract_video_with_progress(request, update_progress)
        
        # Update job status with success
        active_jobs[job_id]["status"] = "completed"
        active_jobs[job_id]["message"] = "Footage extraction completed successfully"
        active_jobs[job_id]["progress"] = 100
        active_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        active_jobs[job_id]["result"] = result
        
        logger.info(f"Extract job {job_id} completed successfully")
        
    except Exception as e:
        # Update job status with error
        active_jobs[job_id]["status"] = "failed"
        active_jobs[job_id]["message"] = f"Video extraction failed: {str(e)}"
        active_jobs[job_id]["progress"] = 0
        active_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        active_jobs[job_id]["error"] = str(e)
        
        logger.error(f"Extract job {job_id} failed: {str(e)}")