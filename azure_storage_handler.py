"""
Azure Blob Storage Handler for scan2epub

Handles uploading local PDF files to Azure Blob Storage with SAS tokens
for temporary access by Azure Content Understanding service.
"""

import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple
from urllib.parse import quote

from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from azure.core.exceptions import AzureError
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()


class AzureStorageHandler:
    """Handles Azure Blob Storage operations for temporary PDF storage"""
    
    def __init__(self, config_manager, debug_mode: bool = False, debug_dir: Optional[Path] = None):
        """
        Initialize Azure Storage Handler
        
        Args:
            config_manager: ConfigManager instance for settings
            debug_mode: True if debug mode is enabled
            debug_dir: Path to the debug directory for saving interim files
        """
        self.config = config_manager
        self.debug_mode = debug_mode
        self.debug_dir = debug_dir
        self.connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        
        if not self.connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING must be set in environment variables")
        
        # Initialize blob service client
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
        self.container_name = self.config.blob_container_name
        
        # Track uploaded blobs for cleanup
        self.uploaded_blobs: List[str] = []
        
        # Ensure container exists
        self._ensure_container_exists()
    
    def _ensure_container_exists(self):
        """Ensure the blob container exists, create if it doesn't"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            if not container_client.exists():
                print(f"Creating blob container: {self.container_name}")
                container_client.create_container()
                print(f"Container created successfully")
        except AzureError as e:
            raise Exception(f"Failed to ensure container exists: {str(e)}")
    
    def _check_file_size(self, file_path: str) -> Tuple[bool, int]:
        """
        Check if file size is within configured limits
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (is_valid, file_size_bytes)
        """
        file_size = os.path.getsize(file_path)
        max_size = self.config.max_file_size_bytes
        
        return file_size <= max_size, file_size
    
    def _generate_unique_blob_name(self, file_path: str) -> str:
        """
        Generate a unique blob name for the file
        
        Args:
            file_path: Original file path
            
        Returns:
            Unique blob name
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        original_name = Path(file_path).name
        # Sanitize filename for Azure
        safe_name = "".join(c for c in original_name if c.isalnum() or c in "._-")
        return f"{timestamp}_{safe_name}"

    def upload_pdf(self, local_path: str) -> str:
        """
        Upload a local PDF file to Azure Blob Storage
        
        Args:
            local_path: Path to the local PDF file
            
        Returns:
            Public URL with SAS token for accessing the file
            
        Raises:
            ValueError: If file is too large or doesn't exist
            Exception: If upload fails
        """
        # Validate file exists
        if not os.path.exists(local_path):
            raise ValueError(f"File not found: {local_path}")
        
        # Check file size
        is_valid_size, file_size = self._check_file_size(local_path)
        if not is_valid_size:
            max_size_mb = self.config.max_file_size_bytes / (1024 * 1024)
            file_size_mb = file_size / (1024 * 1024)
            raise ValueError(f"File too large: {file_size_mb:.1f}MB exceeds limit of {max_size_mb:.1f}MB")
        
        # Generate unique blob name
        blob_name = self._generate_unique_blob_name(local_path)
        
        print(f"Uploading {Path(local_path).name} ({file_size / (1024 * 1024):.1f}MB) to Azure...")
        
        try:
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Upload with progress bar
            with open(local_path, 'rb') as data:
                # Get file size for progress bar
                data.seek(0, 2)  # Seek to end
                total_size = data.tell()
                data.seek(0)  # Seek back to start
                
                # Create progress bar
                with tqdm(total=total_size, unit='B', unit_scale=True, desc="Uploading") as pbar:
                    def progress_callback(current, total):
                        pbar.update(current - pbar.n)
                    
                    # Upload blob
                    blob_client.upload_blob(
                        data,
                        overwrite=True,
                        progress_hook=progress_callback
                    )
            
            print(f"Upload complete: {blob_name}")
            
            # Track this blob for cleanup
            self.uploaded_blobs.append(blob_name)
            
            # Generate SAS URL
            sas_url = self._generate_sas_url(blob_name)
            
            if self.config.debug:
                print(f"Generated SAS URL (valid for {self.config.sas_token_expiry_hours} hour(s))")
            
            return sas_url
            
        except Exception as e:
            # Try to clean up on failure
            try:
                self.delete_blob(blob_name)
            except:
                pass
            # Add more context to the error
            if "Incorrect padding" in str(e):
                raise Exception(f"Failed to generate SAS URL: {str(e)}")
            else:
                raise Exception(f"Failed to upload file: {str(e)}")
    
    def _generate_sas_url(self, blob_name: str) -> str:
        """
        Generate a SAS URL for the blob
        
        Args:
            blob_name: Name of the blob
            
        Returns:
            Full URL with SAS token
        """
        # Get account name from connection string
        account_name = None
        for part in self.connection_string.split(';'):
            if part.startswith('AccountName='):
                account_name = part.split('=', 1)[1]
                break
        
        if not account_name:
            raise ValueError("Could not extract account name from connection string")
        
        # Get account key from connection string
        account_key = None
        for part in self.connection_string.split(';'):
            if part.startswith('AccountKey='):
                account_key = part.split('=', 1)[1]
                break
        
        if not account_key:
            raise ValueError("Could not extract account key from connection string")

        # Debug: Check if account key ends with == (common issue)
        if self.config.debug:
            print(f"DEBUG: Account key length: {len(account_key)}")
            print(f"DEBUG: Account key ends with: ...{account_key[-10:]}")
        
        # Add a check for typical Azure Storage account key length (88 characters)
        if len(account_key) != 88:
            print(f"WARNING: AccountKey length is {len(account_key)}. Azure Storage account keys are typically 88 characters long. "
                  "This might indicate an issue with the key itself.")

        try:
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=self.config.sas_token_expiry_hours)
            )
        except Exception as e:
            if "Incorrect padding" in str(e):
                raise ValueError(
                    "Invalid account key format. Please check your AZURE_STORAGE_CONNECTION_STRING in .env file. "
                    "Make sure the AccountKey part is correct and consider regenerating it from the Azure portal."
                )
            raise
        
        # Construct full URL
        blob_url = f"https://{account_name}.blob.core.windows.net/{self.container_name}/{quote(blob_name)}"
        return f"{blob_url}?{sas_token}"
    
    def delete_blob(self, blob_name: str) -> bool:
        """
        Delete a blob from storage
        
        Args:
            blob_name: Name of the blob to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            blob_client.delete_blob()
            
            if self.config.log_cleanup:
                print(f"Deleted blob: {blob_name}")
            
            # Remove from tracking list
            if blob_name in self.uploaded_blobs:
                self.uploaded_blobs.remove(blob_name)
            
            return True
            
        except Exception as e:
            if self.config.log_cleanup:
                print(f"Failed to delete blob {blob_name}: {str(e)}")
            return False
    
    def cleanup_all(self) -> Tuple[int, int]:
        """
        Clean up all uploaded blobs in this session
        
        Returns:
            Tuple of (successful_deletions, failed_deletions)
        """
        if not self.uploaded_blobs:
            return 0, 0
        
        print(f"\nCleaning up {len(self.uploaded_blobs)} temporary file(s) from Azure...")
        
        successful = 0
        failed = 0
        
        for blob_name in self.uploaded_blobs.copy():  # Copy to avoid modification during iteration
            if self.delete_blob(blob_name):
                successful += 1
            else:
                failed += 1
        
        if self.config.log_cleanup:
            print(f"Cleanup completed: {successful} deleted, {failed} failed")
        
        return successful, failed
    
    def download_all_blobs(self, download_dir: Path) -> Tuple[int, int]:
        """
        Download all uploaded blobs to a specified directory.
        
        Args:
            download_dir: The directory where blobs should be downloaded.
            
        Returns:
            Tuple of (successful_downloads, failed_downloads)
        """
        if not self.uploaded_blobs:
            print("No temporary blobs to download.")
            return 0, 0
        
        # In debug mode, we only want to download blobs that were *not* originally local files.
        # The user already has the original local PDF.
        blobs_to_download = [
            blob_name for blob_name in self.uploaded_blobs
            if not self.is_local_file_blob(blob_name) # Assuming a method to check if it was a local file
        ]

        if not blobs_to_download:
            print("No temporary blobs to download (excluding original local files).")
            return 0, 0
        
        print(f"Downloading {len(blobs_to_download)} temporary file(s) from Azure to {download_dir}...")
        
        successful = 0
        failed = 0
        
        download_dir.mkdir(parents=True, exist_ok=True) # Ensure the directory exists
        
        for blob_name in blobs_to_download:
            try:
                blob_client = self.blob_service_client.get_blob_client(
                    container=self.container_name,
                    blob=blob_name
                )
                download_file_path = download_dir / blob_name
                
                with open(download_file_path, "wb") as download_file:
                    download_file.write(blob_client.download_blob().readall())
                
                print(f"Downloaded blob: {blob_name} to {download_file_path}")
                successful += 1
            except Exception as e:
                print(f"Failed to download blob {blob_name}: {str(e)}")
                failed += 1
        
        print(f"Download completed: {successful} downloaded, {failed} failed")
        return successful, failed

    def is_local_file_blob(self, blob_name: str) -> bool:
        """
        Determines if a blob was uploaded from a local file.
        This is a placeholder and needs a more robust implementation if needed.
        For now, we assume any blob uploaded via upload_pdf is a local file.
        """
        # In a more complex scenario, you might store metadata with the blob
        # or maintain a mapping of original local paths to blob names.
        # For this task, we'll assume all blobs in self.uploaded_blobs originated from local files
        # that the user already possesses.
        return True # For now, assume all uploaded blobs are from local files.

    def is_url(self, path: str) -> bool:
        """
        Check if a path is a URL (http/https)
        
        Args:
            path: Path to check
            
        Returns:
            True if path is a URL, False otherwise
        """
        return path.startswith(('http://', 'https://'))
