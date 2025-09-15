"""
ExacqMan Service

Handles subprocess calls to the ExacqMan CLI tool and manages video processing operations.
"""

import asyncio
import subprocess
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import shutil

from api.models import ExtractRequest, CompressRequest, TimelapseRequest

logger = logging.getLogger(__name__)

class ExacqManService:
    """Service for interacting with ExacqMan CLI tool."""
    
    def __init__(self):
        """Initialize the ExacqMan service."""
        # exacqman.py is always at the same level as exacqman-web directory
        # From backend/services/exacqman_service.py, go up 3 levels to reach ExacqMan root
        self.exacqman_path = str(Path(__file__).parent.parent.parent.parent / "exacqman.py")
        self.working_directory = Path(__file__).parent.parent.parent.parent  # ExacqMan root directory
    
    async def extract_video(self, request: ExtractRequest) -> Dict[str, Any]:
        """
        Extract video from Exacqvision server with timelapse and compression.
        
        Args:
            request: ExtractRequest containing all necessary parameters
            
        Returns:
            Dict containing result information
            
        Raises:
            subprocess.CalledProcessError: If the CLI command fails
        """
        try:
            # Build command arguments
            cmd_args = [
                "python3", self.exacqman_path,
                "extract",
                request.camera_alias,
                request.date,
                request.start_time,
                request.end_time,
                request.config_file
            ]
            
            # Add optional arguments
            if request.server:
                cmd_args.extend(["--server", request.server])
            if request.output_name:
                cmd_args.extend(["-o", request.output_name])
            if request.quality:
                cmd_args.extend(["--quality", request.quality.value])
            if request.multiplier:
                cmd_args.extend(["--multiplier", str(request.multiplier)])
            if request.crop:
                cmd_args.append("-c")
            
            logger.info(f"Running extract command: {' '.join(cmd_args)}")
            
            # Run the command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=self.working_directory,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Extract command failed: {error_msg}")
                raise subprocess.CalledProcessError(process.returncode, cmd_args, error_msg)
            
            # Parse output for result information
            output = stdout.decode() if stdout else ""
            logger.info(f"Extract command completed: {output}")
            
            # Determine output filename
            output_filename = self._determine_output_filename(request, "extract")
            
            return {
                "operation": "extract",
                "output_file": output_filename,
                "status": "completed",
                "message": "Video extraction completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error in extract_video: {str(e)}")
            raise
    
    async def compress_video(self, request: CompressRequest) -> Dict[str, Any]:
        """
        Compress an existing video file.
        
        Args:
            request: CompressRequest containing video file and quality settings
            
        Returns:
            Dict containing result information
            
        Raises:
            subprocess.CalledProcessError: If the CLI command fails
        """
        try:
            # Build command arguments
            cmd_args = [
                "python3", self.exacqman_path,
                "compress",
                request.video_filename,
                request.quality.value
            ]
            
            # Add optional output name
            if request.output_name:
                cmd_args.extend(["-o", request.output_name])
            
            logger.info(f"Running compress command: {' '.join(cmd_args)}")
            
            # Run the command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=self.working_directory,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Compress command failed: {error_msg}")
                raise subprocess.CalledProcessError(process.returncode, cmd_args, error_msg)
            
            # Parse output for result information
            output = stdout.decode() if stdout else ""
            logger.info(f"Compress command completed: {output}")
            
            # Determine output filename
            output_filename = self._determine_output_filename(request, "compress")
            
            return {
                "operation": "compress",
                "output_file": output_filename,
                "status": "completed",
                "message": "Video compression completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error in compress_video: {str(e)}")
            raise
    
    async def create_timelapse(self, request: TimelapseRequest) -> Dict[str, Any]:
        """
        Create a timelapse from an existing video file.
        
        Args:
            request: TimelapseRequest containing video file and timelapse settings
            
        Returns:
            Dict containing result information
            
        Raises:
            subprocess.CalledProcessError: If the CLI command fails
        """
        try:
            # Build command arguments
            cmd_args = [
                "python3", self.exacqman_path,
                "timelapse",
                request.video_filename,
                str(request.multiplier)
            ]
            
            # Add optional arguments
            if request.output_name:
                cmd_args.extend(["-o", request.output_name])
            if request.crop:
                cmd_args.append("-c")
            
            logger.info(f"Running timelapse command: {' '.join(cmd_args)}")
            
            # Run the command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=self.working_directory,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Timelapse command failed: {error_msg}")
                raise subprocess.CalledProcessError(process.returncode, cmd_args, error_msg)
            
            # Parse output for result information
            output = stdout.decode() if stdout else ""
            logger.info(f"Timelapse command completed: {output}")
            
            # Determine output filename
            output_filename = self._determine_output_filename(request, "timelapse")
            
            return {
                "operation": "timelapse",
                "output_file": output_filename,
                "status": "completed",
                "message": "Timelapse creation completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error in create_timelapse: {str(e)}")
            raise
    
    def _determine_output_filename(self, request, operation: str) -> str:
        """
        Determine the output filename based on the request and operation.
        
        Args:
            request: The request object
            operation: The operation type (extract, compress, timelapse)
            
        Returns:
            The expected output filename
        """
        if hasattr(request, 'output_name') and request.output_name:
            return request.output_name
        
        # For extract operation, we need to construct the filename
        if operation == "extract":
            # This would need to be coordinated with the actual ExacqMan output
            # For now, return a placeholder
            return f"extracted_{request.camera_alias}_{request.date.replace('/', '_')}.mp4"
        
        # For compress and timelapse, modify the input filename
        input_file = request.video_filename
        name, ext = os.path.splitext(input_file)
        
        if operation == "compress":
            return f"{name}_{request.quality.value}{ext}"
        elif operation == "timelapse":
            return f"{name}_{request.multiplier}x{ext}"
        
        return input_file
    
    def validate_config_file(self, config_path: str) -> bool:
        """
        Validate that a config file exists and is readable.
        
        Args:
            config_path: Path to the config file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            full_path = Path(config_path)
            if not full_path.is_absolute():
                full_path = self.working_directory / config_path
            
            return full_path.exists() and full_path.is_file()
        except Exception:
            return False
    
    def get_available_configs(self) -> list:
        """
        Get list of available configuration files.
        
        Returns:
            List of config file paths
        """
        config_files = []
        config_dir = self.working_directory
        
        # Look for .config files
        for file_path in config_dir.glob("*.config"):
            config_files.append(str(file_path))
        
        return config_files
