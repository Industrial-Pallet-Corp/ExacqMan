"""
ExacqMan Service

Handles interaction with the ExacqMan CLI tool for video processing operations.
"""

import asyncio
import subprocess
import logging
import time
from typing import Dict, Any, Callable
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
    
    async def extract_video_with_progress(self, request: ExtractRequest, progress_callback: Callable[[int, str], None]) -> Dict[str, Any]:
        """
        Extract video with real-time progress tracking.
        
        Args:
            request: ExtractRequest containing all necessary parameters
            progress_callback: Function to call with progress updates (progress_percent, message)
            
        Returns:
            Dict containing result information
        """
        try:
            # Convert datetime objects to the format expected by ExacqMan CLI
            start_date = request.start_datetime.strftime("%m/%d")
            start_time = request.start_datetime.strftime("%I:%M%p").lstrip('0')
            end_time = request.end_datetime.strftime("%I:%M%p").lstrip('0')
            
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
                "-c",  # Enable cropping to apply crop_dimensions and font_weight settings
                "-o", output_filename
            ]
            
            # Add optional server argument
            if request.server:
                cmd_args.extend(["--server", request.server])
            
            logger.info(f"Running extract command: {' '.join(cmd_args)}")
            logger.info(f"Working directory: {self.working_directory}")
            logger.info(f"Config file: {request.config_file}")
            
            # Initial progress
            progress_callback(0, "Starting video extraction...")
            
            # Run the command asynchronously with real-time output parsing
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=self.working_directory,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT  # Combine stderr with stdout
            )
            
            # Parse output in real-time
            progress_percent = 0
            last_incremental_time = time.time()
            
            while True:
                # Check for incremental progress first (every 2 seconds)
                current_time = time.time()
                if current_time - last_incremental_time >= 2.0 and progress_percent < 90:
                    # Calculate next milestone
                    next_milestone = 20 if progress_percent < 20 else (30 if progress_percent < 30 else 90)
                    increment = min(2, next_milestone - progress_percent)
                    if increment > 0:
                        progress_percent += increment
                        last_incremental_time = current_time
                        
                        # Update message based on current stage
                        if progress_percent < 20:
                            message = "Footage located..."
                        elif progress_percent < 30:
                            message = "Footage extracted successfully..."
                        else:
                            message = "Processing footage..."
                        
                        logger.info(f"Incremental progress: {message} ({progress_percent}%)")
                        progress_callback(progress_percent, message)
                
                # Read CLI output with timeout
                try:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=0.1)
                    if not line:
                        break
                    
                    # Decode bytes to string
                    line = line.decode('utf-8').strip()
                    if not line:
                        continue
                    
                    logger.info(f"CLI Output: {line}")
                    
                    # Check for milestone updates
                    if "Export ready" in line:
                        progress_percent = 10
                        last_incremental_time = time.time()
                        progress_callback(progress_percent, "Footage located...")
                    elif "Video saved successfully" in line:
                        progress_percent = 20
                        last_incremental_time = time.time()
                        progress_callback(progress_percent, "Footage extracted successfully...")
                    elif "Processing Video" in line:
                        progress_percent = 30
                        last_incremental_time = time.time()
                        progress_callback(progress_percent, "Processing footage...")
                    elif "Beginning Video compression" in line:
                        progress_percent = 90
                        last_incremental_time = time.time()
                        progress_callback(progress_percent, "Compressing footage...")
                    elif "Video successfully compressed" in line:
                        progress_callback(100, "Video processing completed!")
                        break
                        
                except asyncio.TimeoutError:
                    # No output available, continue with incremental progress
                    continue
            
            # Wait for process to complete
            await process.wait()
            
            if process.returncode != 0:
                error_msg = f"Extract command failed with return code {process.returncode}"
                logger.error(error_msg)
                progress_callback(0, f"Error: {error_msg}")
                raise subprocess.CalledProcessError(process.returncode, cmd_args, error_msg)
            
            # Move final output to exports directory
            final_path = await self._move_to_exports(output_filename)
            
            # Clean up intermediate files after moving the final file
            await self._cleanup_intermediate_files(output_filename)
            
            return {
                "operation": "extract",
                "output_file": final_path,
                "filename": Path(final_path).name,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error in extract_video_with_progress: {str(e)}")
            progress_callback(0, f"Error: {str(e)}")
            raise

    def _generate_output_filename(self, request: ExtractRequest) -> str:
        """
        Generate a consistent output filename for the extract operation.
        
        Args:
            request: ExtractRequest object
            
        Returns:
            Generated filename (without .mp4 extension, as exacqman.py adds it automatically)
        """
        date_str = request.start_datetime.strftime("%Y-%m-%d")
        time_str = self._format_time_for_filename(request.start_datetime)
        return f"{date_str}_{time_str}_{request.camera_alias}_{request.timelapse_multiplier}x"
    
    def _format_time_for_filename(self, datetime_obj) -> str:
        """
        Format datetime for filename: 9:15am becomes 0915am, 11:45pm becomes 1145pm
        
        Args:
            datetime_obj: datetime object
            
        Returns:
            Formatted time string for filename
        """
        # Get hour and minute
        hour = datetime_obj.hour
        minute = datetime_obj.minute
        
        # Convert to 12-hour format
        if hour == 0:
            hour_12 = 12
            period = 'am'
        elif hour < 12:
            hour_12 = hour
            period = 'am'
        elif hour == 12:
            hour_12 = 12
            period = 'pm'
        else:
            hour_12 = hour - 12
            period = 'pm'
        
        # Format as HHMMam/pm (zero-padded)
        return f"{hour_12:02d}{minute:02d}{period}"
    
    async def _cleanup_intermediate_files(self, base_filename: str = None):
        """
        Clean up intermediate files created during video processing.
        
        This removes temporary files that ExacqMan creates during processing
        but keeps only the final compressed output.
        
        Args:
            base_filename: Base filename to clean up specific intermediate files
        """
        try:
            cleaned_files = []
            
            # Clean up specific intermediate files if base_filename is provided
            if base_filename:
                base_name = base_filename.replace('.mp4', '')
                
                # Patterns for intermediate files specific to this extraction
                specific_patterns = [
                    f"{base_name}.mp4",  # Raw export
                    f"{base_name}_*.mp4",  # Timelapsed version (before compression)
                ]
                
                for pattern in specific_patterns:
                    for file_path in self.working_directory.glob(pattern):
                        if file_path.is_file():
                            # Skip the final compressed file
                            if not any(compression in file_path.name for compression in ['_libx264_', '_high', '_medium', '_low']):
                                file_path.unlink()
                                cleaned_files.append(file_path.name)
                                logger.info(f"Cleaned up intermediate file: {file_path.name}")
            
            # Clean up general temporary files
            general_patterns = [
                "*.tmp",
                "*_temp.*",
                "*_intermediate.*",
                "temp_*",
                "*.log"
            ]
            
            for pattern in general_patterns:
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
        Move the final compressed file to the exports directory.
        
        Args:
            filename: Base name of the file to move (exacqman.py may create variations)
            
        Returns:
            Path to the file in exports directory
        """
        try:
            # Create exports directory if it doesn't exist
            exports_dir = self.working_directory / "exacqman-web" / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            
            # Look for the final compressed file with any compression level
            base_name = filename.replace('.mp4', '')  # Remove .mp4 if present
            source_path = None
            
            # Try to find the final compressed file with libx264 pattern
            for file_path in self.working_directory.glob(f"{base_name}_*_libx264_*.mp4"):
                if file_path.is_file():
                    source_path = file_path
                    break
            
            # If not found, try the specific high compression pattern
            if not source_path:
                final_filename = f"{base_name}_libx264_high.mp4"
                source_path = self.working_directory / final_filename
                if not source_path.exists():
                    source_path = None
            
            # Fallback to original filename if no compressed version found
            if not source_path:
                source_path = self.working_directory / filename
                if not source_path.exists():
                    source_path = self.working_directory / f"{filename}.mp4"
            
            if not source_path or not source_path.exists():
                raise FileNotFoundError(f"Final compressed file not found for: {filename}")
            
            # Move to exports directory with clean filename
            clean_filename = f"{base_name}.mp4"
            dest_path = exports_dir / clean_filename
            shutil.move(str(source_path), str(dest_path))
            
            logger.info(f"Moved final compressed file {source_path.name} to exports directory as {clean_filename}")
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