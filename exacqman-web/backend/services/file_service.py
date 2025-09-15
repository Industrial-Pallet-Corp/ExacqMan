"""
File Service

Handles file operations including upload, download, and file management.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import UploadFile

from api.models import FileInfo

logger = logging.getLogger(__name__)

class FileService:
    """Service for handling file operations."""
    
    def __init__(self):
        """Initialize the file service."""
        self.uploads_dir = Path("uploads")
        self.exports_dir = Path("exports")
        self.allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'}
        
        # Ensure directories exist
        self.uploads_dir.mkdir(exist_ok=True)
        self.exports_dir.mkdir(exist_ok=True)
    
    def save_uploaded_file(self, file: UploadFile) -> str:
        """
        Save an uploaded file to the uploads directory.
        
        Args:
            file: FastAPI UploadFile object
            
        Returns:
            Path to the saved file
            
        Raises:
            ValueError: If file type is not allowed
        """
        try:
            # Validate file extension
            file_extension = Path(file.filename).suffix.lower()
            if file_extension not in self.allowed_extensions:
                raise ValueError(f"File type {file_extension} is not allowed")
            
            # Create safe filename
            safe_filename = self._create_safe_filename(file.filename)
            file_path = self.uploads_dir / safe_filename
            
            # Handle filename conflicts
            file_path = self._resolve_filename_conflict(file_path)
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            logger.info(f"File uploaded successfully: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error saving uploaded file: {str(e)}")
            raise
    
    def list_video_files(self) -> List[FileInfo]:
        """
        List all video files in the exports directory.
        
        Returns:
            List of FileInfo objects
        """
        try:
            files = []
            
            # Check exports directory
            for file_path in self.exports_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in self.allowed_extensions:
                    file_info = self._create_file_info(file_path)
                    files.append(file_info)
            
            # Check uploads directory
            for file_path in self.uploads_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in self.allowed_extensions:
                    file_info = self._create_file_info(file_path)
                    files.append(file_info)
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x.modified_at, reverse=True)
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing video files: {str(e)}")
            raise
    
    def get_file_path(self, filename: str) -> str:
        """
        Get the full path to a file.
        
        Args:
            filename: Name of the file
            
        Returns:
            Full path to the file
            
        Raises:
            FileNotFoundError: If file is not found
        """
        # Check exports directory first
        exports_path = self.exports_dir / filename
        if exports_path.exists():
            return str(exports_path)
        
        # Check uploads directory
        uploads_path = self.uploads_dir / filename
        if uploads_path.exists():
            return str(uploads_path)
        
        raise FileNotFoundError(f"File not found: {filename}")
    
    def delete_file(self, filename: str) -> bool:
        """
        Delete a file from the server.
        
        Args:
            filename: Name of the file to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            file_path = Path(self.get_file_path(filename))
            file_path.unlink()
            logger.info(f"File deleted successfully: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {str(e)}")
            return False
    
    def get_file_size(self, file_path: str) -> int:
        """
        Get the size of a file in bytes.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File size in bytes
        """
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0
    
    def _create_safe_filename(self, filename: str) -> str:
        """
        Create a safe filename by removing or replacing unsafe characters.
        
        Args:
            filename: Original filename
            
        Returns:
            Safe filename
        """
        # Remove or replace unsafe characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"
        safe_filename = "".join(c if c in safe_chars else "_" for c in filename)
        
        # Ensure it's not empty
        if not safe_filename:
            safe_filename = "uploaded_file"
        
        return safe_filename
    
    def _resolve_filename_conflict(self, file_path: Path) -> Path:
        """
        Resolve filename conflicts by adding a number suffix.
        
        Args:
            file_path: Original file path
            
        Returns:
            Resolved file path
        """
        if not file_path.exists():
            return file_path
        
        counter = 1
        name = file_path.stem
        extension = file_path.suffix
        parent = file_path.parent
        
        while True:
            new_name = f"{name}_{counter}{extension}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1
    
    def _create_file_info(self, file_path: Path) -> FileInfo:
        """
        Create a FileInfo object from a file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            FileInfo object
        """
        try:
            stat = file_path.stat()
            
            return FileInfo(
                filename=file_path.name,
                path=str(file_path),
                size=stat.st_size,
                created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                file_type=file_path.suffix.lower()
            )
        except Exception as e:
            logger.error(f"Error creating file info for {file_path}: {str(e)}")
            # Return minimal file info
            return FileInfo(
                filename=file_path.name,
                path=str(file_path),
                size=0,
                created_at=datetime.now().isoformat(),
                modified_at=datetime.now().isoformat(),
                file_type=file_path.suffix.lower()
            )
    
    def cleanup_old_files(self, max_age_days: int = 7) -> int:
        """
        Clean up old files from the uploads directory.
        
        Args:
            max_age_days: Maximum age of files in days
            
        Returns:
            Number of files deleted
        """
        try:
            deleted_count = 0
            cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
            
            for file_path in self.uploads_dir.iterdir():
                if file_path.is_file():
                    file_age = file_path.stat().st_mtime
                    if file_age < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(f"Cleaned up old file: {file_path.name}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during file cleanup: {str(e)}")
            return 0
