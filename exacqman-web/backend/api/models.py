"""
Data models for ExacqMan Web API

Defines Pydantic models for request/response validation and serialization.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class QualityLevel(str, Enum):
    """Video quality levels for compression."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class JobStatusEnum(str, Enum):
    """Job status enumeration."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ExtractRequest(BaseModel):
    """Request model for video extraction."""
    camera_alias: str = Field(..., description="Camera alias from config")
    date: str = Field(..., description="Date in MM/DD format (e.g., '3/11')")
    start_time: str = Field(..., description="Start time (e.g., '6 pm', '18:30')")
    end_time: str = Field(..., description="End time (e.g., '6 pm', '18:30')")
    config_file: str = Field(..., description="Path to config file")
    server: Optional[str] = Field(None, description="Server location initials")
    output_name: Optional[str] = Field(None, description="Desired output filename")
    quality: Optional[QualityLevel] = Field(QualityLevel.MEDIUM, description="Video quality")
    multiplier: Optional[int] = Field(10, description="Timelapse multiplier")
    crop: Optional[bool] = Field(False, description="Enable video cropping")
    
    @validator('multiplier')
    def validate_multiplier(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Multiplier must be a positive integer')
        return v
    
    @validator('date')
    def validate_date(cls, v):
        # Basic date format validation
        try:
            parts = v.split('/')
            if len(parts) != 2:
                raise ValueError('Date must be in MM/DD format')
            month, day = int(parts[0]), int(parts[1])
            if not (1 <= month <= 12) or not (1 <= day <= 31):
                raise ValueError('Invalid date values')
        except (ValueError, IndexError):
            raise ValueError('Date must be in MM/DD format (e.g., "3/11")')
        return v

class CompressRequest(BaseModel):
    """Request model for video compression."""
    video_filename: str = Field(..., description="Path to video file to compress")
    quality: QualityLevel = Field(QualityLevel.MEDIUM, description="Compression quality")
    output_name: Optional[str] = Field(None, description="Desired output filename")

class TimelapseRequest(BaseModel):
    """Request model for timelapse creation."""
    video_filename: str = Field(..., description="Path to video file for timelapse")
    multiplier: int = Field(10, description="Timelapse multiplier")
    output_name: Optional[str] = Field(None, description="Desired output filename")
    crop: Optional[bool] = Field(False, description="Enable video cropping")
    
    @validator('multiplier')
    def validate_multiplier(cls, v):
        if v <= 0:
            raise ValueError('Multiplier must be a positive integer')
        return v

class JobStatus(BaseModel):
    """Job status response model."""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatusEnum = Field(..., description="Current job status")
    progress: int = Field(..., description="Progress percentage (0-100)")
    message: str = Field(..., description="Status message")
    created_at: str = Field(..., description="Job creation timestamp")
    completed_at: Optional[str] = Field(None, description="Job completion timestamp")
    result: Optional[Dict[str, Any]] = Field(None, description="Job result data")

class FileInfo(BaseModel):
    """File information model."""
    filename: str = Field(..., description="File name")
    path: str = Field(..., description="File path")
    size: int = Field(..., description="File size in bytes")
    created_at: str = Field(..., description="File creation timestamp")
    modified_at: str = Field(..., description="File modification timestamp")
    file_type: str = Field(..., description="File type/extension")

class ApiResponse(BaseModel):
    """Generic API response model."""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if failed")

class ConfigInfo(BaseModel):
    """Configuration information model."""
    config_file: str = Field(..., description="Path to config file")
    servers: Dict[str, str] = Field(..., description="Available servers")
    cameras: Dict[str, str] = Field(..., description="Available cameras")
    settings: Dict[str, Any] = Field(..., description="Configuration settings")

class UploadResponse(BaseModel):
    """File upload response model."""
    filename: str = Field(..., description="Uploaded file name")
    path: str = Field(..., description="File path on server")
    size: int = Field(..., description="File size in bytes")
    message: str = Field(..., description="Upload status message")
