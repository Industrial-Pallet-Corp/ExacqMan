"""
Configuration Service

Handles reading and managing ExacqMan configuration files for the web application.
"""

import configparser
import logging
from pathlib import Path
from typing import List, Dict, Optional
from api.models import CameraInfo, ConfigInfo

logger = logging.getLogger(__name__)

class ConfigService:
    """Service for managing ExacqMan configuration files."""
    
    def __init__(self):
        """Initialize the configuration service."""
        self.working_directory = Path(__file__).parent.parent.parent.parent  # ExacqMan root
        self.timelapse_options = [2, 5, 10, 15, 20, 25, 30, 40, 50]
    
    def get_available_cameras(self, config_file: str) -> List[CameraInfo]:
        """
        Get list of available cameras from configuration file.
        
        Args:
            config_file: Path to the configuration file
            
        Returns:
            List of CameraInfo objects
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            configparser.Error: If config file is invalid
        """
        try:
            config_path = Path(config_file)
            if not config_path.is_absolute():
                config_path = self.working_directory / config_file
            
            if not config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_file}")
            
            config = configparser.ConfigParser()
            config.read(config_path)
            
            if 'Cameras' not in config:
                logger.warning(f"No [Cameras] section found in {config_file}")
                return []
            
            cameras = []
            for alias, camera_id in config['Cameras'].items():
                cameras.append(CameraInfo(
                    alias=alias,
                    id=camera_id,
                    description=f"Camera {alias} (ID: {camera_id})"
                ))
            
            logger.info(f"Loaded {len(cameras)} cameras from {config_file}")
            return cameras
            
        except Exception as e:
            logger.error(f"Error reading cameras from config {config_file}: {str(e)}")
            raise
    
    def get_available_servers(self, config_file: str) -> Dict[str, str]:
        """
        Get list of available servers from configuration file.
        
        Args:
            config_file: Path to the configuration file
            
        Returns:
            Dictionary of server names to IP addresses
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            configparser.Error: If config file is invalid
        """
        try:
            config_path = Path(config_file)
            if not config_path.is_absolute():
                config_path = self.working_directory / config_file
            
            if not config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_file}")
            
            config = configparser.ConfigParser()
            config.read(config_path)
            
            if 'Network' not in config:
                logger.warning(f"No [Network] section found in {config_file}")
                return {}
            
            servers = dict(config['Network'])
            logger.info(f"Loaded {len(servers)} servers from {config_file}")
            return servers
            
        except Exception as e:
            logger.error(f"Error reading servers from config {config_file}: {str(e)}")
            raise
    
    def get_config_info(self, config_file: str) -> ConfigInfo:
        """
        Get complete configuration information.
        
        Args:
            config_file: Path to the configuration file
            
        Returns:
            ConfigInfo object with all configuration data
        """
        try:
            cameras = self.get_available_cameras(config_file)
            servers = self.get_available_servers(config_file)
            
            return ConfigInfo(
                cameras=cameras,
                servers=servers,
                timelapse_options=self.timelapse_options
            )
            
        except Exception as e:
            logger.error(f"Error getting config info from {config_file}: {str(e)}")
            raise
    
    def validate_camera(self, config_file: str, camera_alias: str) -> bool:
        """
        Validate that a camera alias exists in the configuration.
        
        Args:
            config_file: Path to the configuration file
            camera_alias: Camera alias to validate
            
        Returns:
            True if camera exists, False otherwise
        """
        try:
            cameras = self.get_available_cameras(config_file)
            return any(camera.alias == camera_alias for camera in cameras)
        except Exception as e:
            logger.error(f"Error validating camera {camera_alias}: {str(e)}")
            return False
    
    def get_camera_id(self, config_file: str, camera_alias: str) -> Optional[str]:
        """
        Get the camera ID for a given alias.
        
        Args:
            config_file: Path to the configuration file
            camera_alias: Camera alias to look up
            
        Returns:
            Camera ID if found, None otherwise
        """
        try:
            cameras = self.get_available_cameras(config_file)
            for camera in cameras:
                if camera.alias == camera_alias:
                    return camera.id
            return None
        except Exception as e:
            logger.error(f"Error getting camera ID for {camera_alias}: {str(e)}")
            return None
    
    def get_available_config_files(self) -> List[str]:
        """
        Get list of available configuration files in the ExacqMan directory.
        
        Returns:
            List of configuration file paths
        """
        try:
            config_files = []
            for file_path in self.working_directory.glob("*.config"):
                config_files.append(str(file_path))
            
            logger.info(f"Found {len(config_files)} configuration files")
            return config_files
            
        except Exception as e:
            logger.error(f"Error finding config files: {str(e)}")
            return []
    
    def validate_config_file(self, config_file: str) -> bool:
        """
        Validate that a configuration file exists and is readable.
        
        Args:
            config_file: Path to the configuration file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            config_path = Path(config_file)
            if not config_path.is_absolute():
                config_path = self.working_directory / config_file
            
            if not config_path.exists():
                return False
            
            # Try to parse the config file
            config = configparser.ConfigParser()
            config.read(config_path)
            
            # Check for required sections
            required_sections = ['Auth', 'Network', 'Cameras', 'Settings']
            return all(section in config for section in required_sections)
            
        except Exception as e:
            logger.error(f"Error validating config file {config_file}: {str(e)}")
            return False
