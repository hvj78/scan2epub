"""
Configuration Manager for scan2epub

Handles user configuration using INI format for ease of use.
Provides defaults and validation for all settings.
"""

import configparser
from pathlib import Path
from typing import Any, Optional


class ConfigManager:
    """Manages configuration settings for scan2epub"""
    
    DEFAULT_CONFIG = {
        'Storage': {
            'max_file_size_mb': '256',
            'blob_container_name': 'scan2epub-temp',
            'sas_token_expiry_hours': '1'
        },
        'Processing': {
            'debug': 'false',
            'save_interim': 'false'
        },
        'Cleanup': {
            'cleanup_on_failure': 'true',
            'log_cleanup': 'true'
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            config_path: Path to configuration file. If None, looks for scan2epub.ini
                         in current directory, then uses defaults.
        """
        self.config = configparser.ConfigParser()
        
        # Set defaults
        for section, options in self.DEFAULT_CONFIG.items():
            self.config[section] = options
        
        # Determine config file path
        if config_path is None:
            config_path = 'scan2epub.ini'
        
        self.config_path = Path(config_path)
        
        # Load user configuration if exists
        if self.config_path.exists():
            try:
                self.config.read(self.config_path)
                print(f"Loaded configuration from: {self.config_path}")
            except Exception as e:
                print(f"Warning: Failed to load config file {self.config_path}: {e}")
                print("Using default configuration")
        else:
            print(f"No configuration file found at {self.config_path}, using defaults")
            # Create a template config file for user reference
            self._create_template_config()
    
    def _create_template_config(self):
        """Create a template configuration file with comments"""
        template_content = """# scan2epub Configuration File
# 
# This file controls various settings for the scan2epub tool.
# Lines starting with # are comments and are ignored.
# To change a setting, remove the # at the beginning of the line and modify the value.

[Storage]
# Maximum file size in MB for local PDF uploads
# Files larger than this will be rejected with an error message
max_file_size_mb = 256

# Name of the Azure Blob Storage container for temporary files
# This container must exist in your Azure storage account
blob_container_name = scan2epub-temp

# How long (in hours) the temporary URLs should remain valid
# After this time, the URLs will expire and files cannot be accessed
sas_token_expiry_hours = 1

[Processing]
# Enable debug output for troubleshooting
# Set to true to see detailed processing information
debug = false

# Save interim results to disk to reduce memory usage
# Useful for processing very large books
save_interim = false

[Cleanup]
# Always attempt to clean up temporary files, even if processing fails
# Recommended to keep this as true to avoid accumulating files in Azure
cleanup_on_failure = true

# Log cleanup operations to track what was deleted
# Useful for debugging and auditing
log_cleanup = true
"""
        
        template_path = self.config_path.with_suffix('.ini.template')
        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
            print(f"Created configuration template at: {template_path}")
        except Exception as e:
            print(f"Warning: Could not create config template: {e}")
    
    def get(self, section: str, option: str, fallback: Any = None) -> Any:
        """
        Get a configuration value
        """
        return self.config.get(section, option, fallback=fallback)
    
    def getint(self, section: str, option: str, fallback: int = 0) -> int:
        """Get a configuration value as integer"""
        return self.config.getint(section, option, fallback=fallback)
    
    def getfloat(self, section: str, option: str, fallback: float = 0.0) -> float:
        """Get a configuration value as float"""
        return self.config.getfloat(section, option, fallback=fallback)
    
    def getboolean(self, section: str, option: str, fallback: bool = False) -> bool:
        """Get a configuration value as boolean"""
        return self.config.getboolean(section, option, fallback=fallback)
    
    @property
    def max_file_size_bytes(self) -> int:
        """Get maximum file size in bytes"""
        mb = self.getint('Storage', 'max_file_size_mb', 256)
        return mb * 1024 * 1024
    
    @property
    def blob_container_name(self) -> str:
        """Get blob container name"""
        return self.get('Storage', 'blob_container_name', 'scan2epub-temp')
    
    @property
    def sas_token_expiry_hours(self) -> int:
        """Get SAS token expiry in hours"""
        return self.getint('Storage', 'sas_token_expiry_hours', 1)
    
    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled"""
        return self.getboolean('Processing', 'debug', False)
    
    @property
    def save_interim(self) -> bool:
        """Check if interim results should be saved"""
        return self.getboolean('Processing', 'save_interim', False)
    
    @property
    def cleanup_on_failure(self) -> bool:
        """Check if cleanup should run on failure"""
        return self.getboolean('Cleanup', 'cleanup_on_failure', True)
    
    @property
    def log_cleanup(self) -> bool:
        """Check if cleanup operations should be logged"""
        return self.getboolean('Cleanup', 'log_cleanup', True)
