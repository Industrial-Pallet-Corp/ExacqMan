"""
ExacqMan Service

Handles interaction with the ExacqMan CLI tool for video processing operations.
"""

import asyncio
import subprocess
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import shutil

from api.models import ExtractRequest

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
            # Convert datetime objects to the format expected by ExacqMan CLI
            start_date = request.start_datetime.strftime("%m/%d")
            start_time = request.start_datetime.strftime("%I:%M %p").lstrip('0')
            end_time = request.end_datetime.strftime("%I:%M %p").lstrip('0')
            
            # Generate output filename
            output_filename = self._generate_output_filename(request)
            
            # Build command arguments
            cmd_args = [
                "python3", self.exacqman_path,
                "extract",
                request.camera_alias,
                start_date,
                start_time,
                end_time,
                request.config_file,
                "--multiplier", str(request.timelapse_multiplier),
                "-o", output_filename
            ]
            
            # Add optional server argument
            if request.server:
                cmd_args.extend(["--server", request.server])
            
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
            
            # Clean up intermediate files
            await self._cleanup_intermediate_files()
            
            # Move final output to exports directory
            final_path = await self._move_to_exports(output_filename)
            
            return {
                "operation": "extract",
                "output_file": final_path,
                "filename": Path(final_path).name,
                "status": "completed",
                "message": "Video extraction completed successfully",
                "cleanup_completed": True
            }
            
        except Exception as e:
            logger.error(f"Error in extract_video: {str(e)}")
            # Try to clean up even if extraction failed
            try:
                await self._cleanup_intermediate_files()
            except Exception as cleanup_error:
                logger.error(f"Cleanup failed after extraction error: {cleanup_error}")
            raise
    
    def _generate_output_filename(self, request: ExtractRequest) -> str:
        """
        Generate a consistent output filename for the extract operation.
        
        Args:
            request: ExtractRequest object
            
        Returns:
            Generated filename
        """
        date_str = request.start_datetime.strftime("%Y-%m-%d")
        return f"{date_str}_{request.camera_alias}_{request.timelapse_multiplier}x.mp4"
    
    async def _cleanup_intermediate_files(self):
        """
        Clean up intermediate files created during video processing.
        
        This removes temporary files that ExacqMan creates during processing
        but keeps only the final output.
        """
        try:
            # Look for common intermediate file patterns
            intermediate_patterns = [
                "*.tmp",
                "*_temp.*",
                "*_intermediate.*",
                "temp_*",
                "*.log"
            ]
            
            cleaned_files = []
            for pattern in intermediate_patterns:
                for file_path in self.working_directory.glob(pattern):
                    if file_path.is_file():
                        file_path.unlink()
                        cleaned_files.append(file_path.name)
            
            if cleaned_files:
                logger.info(f"Cleaned up {len(cleaned_files)} intermediate files: {cleaned_files}")
            else:
                logger.info("No intermediate files found to clean up")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            # Don't raise the exception as cleanup failure shouldn't fail the job
    
    async def _move_to_exports(self, filename: str) -> str:
        """
        Move the final output file to the exports directory.
        
        Args:
            filename: Name of the file to move
            
        Returns:
            Path to the file in exports directory
        """
        try:
            # Create exports directory if it doesn't exist
            exports_dir = self.working_directory / "exacqman-web" / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            
            # Look for the file in the working directory
            source_path = self.working_directory / filename
            if not source_path.exists():
                # Try with .mp4 extension if not found
                source_path = self.working_directory / f"{filename}.mp4"
            
            if not source_path.exists():
                raise FileNotFoundError(f"Output file not found: {filename}")
            
            # Move to exports directory
            dest_path = exports_dir / source_path.name
            shutil.move(str(source_path), str(dest_path))
            
            logger.info(f"Moved {source_path.name} to exports directory")
            return str(dest_path)
            
        except Exception as e:
            logger.error(f"Error moving file to exports: {str(e)}")
            raise
    
    def validate_config_file(self, config_path: str) -> bool:
        """
        Validate that a config file exists and is readable.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not config_path.startswith('/'):
                config_path = str(self.working_directory / config_path)
            
            return Path(config_path).exists()
        except Exception as e:
            logger.error(f"Error validating config file {config_path}: {str(e)}")
            return False
    
    def get_available_configs(self) -> list:
        """
        Get list of available configuration files.
        
        Returns:
            List of configuration file paths
        """
        try:
            config_files = []
            for file_path in self.working_directory.glob("*.config"):
                config_files.append(str(file_path))
            return config_files
        except Exception as e:
            logger.error(f"Error getting available configs: {str(e)}")
            return []