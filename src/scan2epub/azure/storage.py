"""
Azure Blob Storage Handler for scan2epub

Handles uploading local PDF files to Azure Blob Storage with SAS tokens
for temporary access by Azure Content Understanding service.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple
from urllib.parse import quote

from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from azure.core.exceptions import AzureError
from tqdm import tqdm

from scan2epub.utils.errors import StorageError


class AzureStorageHandler:
    """Handles Azure Blob Storage operations for temporary PDF storage"""
    
    def __init__(self, config_manager, debug_mode: bool = False, debug_dir: Optional[Path] = None):
        """
        Initialize Azure Storage Handler
        
        Args:
            config_manager: ConfigManager-like instance for settings
            debug_mode: True if debug mode is enabled
            debug_dir: Path to the debug directory for saving interim files
        """
        self.config = config_manager
        self.debug_mode = debug_mode
        self.debug_dir = debug_dir
        self.connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        
        if not self.connection_string:
            raise StorageError("AZURE_STORAGE_CONNECTION_STRING must be set in environment variables")
        
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
            raise StorageError(f"Failed to ensure container exists: {str(e)}")
    
    def _check_file_size(self, file_path: str) -> Tuple[bool, int]:
        """
        Check if file size is within configured limits
        """
        file_size = os.path.getsize(file_path)
        max_size = self.config.max_file_size_bytes
        return file_size <= max_size, file_size
    
    def _generate_unique_blob_name(self, file_path: str) -> str:
        """
        Generate a unique blob name for the file
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        original_name = Path(file_path).name
        # Sanitize filename for Azure
        safe_name = "".join(c for c in original_name if c.isalnum() or c in "._-")
        return f"{timestamp}_{safe_name}"

    def upload_pdf(self, local_path: str) -> str:
        """
        Upload a local PDF file to Azure Blob Storage and return a SAS URL
        """
        # Validate file exists
        if not os.path.exists(local_path):
            raise StorageError(f"File not found: {local_path}")
        
        # Check file size
        is_valid_size, file_size = self._check_file_size(local_path)
        if not is_valid_size:
            max_size_mb = self.config.max_file_size_bytes / (1024 * 1024)
            file_size_mb = file_size / (1024 * 1024)
            raise StorageError(f"File too large: {file_size_mb:.1f}MB exceeds limit of {max_size_mb:.1f}MB")
        
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
                
                with tqdm(total=total_size, unit='B', unit_scale=True, desc="Uploading") as pbar:
                    def progress_callback(current, total):
                        pbar.update(current - pbar.n)
                    
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
            except Exception:
                pass
            if "Incorrect padding" in str(e):
                raise StorageError(f"Failed to generate SAS URL: {str(e)}")
            else:
                raise StorageError(f"Failed to upload file: {str(e)}")
    
    def _generate_sas_url(self, blob_name: str) -> str:
        """
        Generate a SAS URL for the blob
        """
        # Get account name
        account_name = None
        for part in self.connection_string.split(';'):
            if part.startswith('AccountName='):
                account_name = part.split('=', 1)[1]
                break
        if not account_name:
            raise StorageError("Could not extract account name from connection string")
        
        # Get account key
        account_key = None
        for part in self.connection_string.split(';'):
            if part.startswith('AccountKey='):
                account_key = part.split('=', 1)[1]
                break
        if not account_key:
            raise StorageError("Could not extract account key from connection string")
        
        # Add a check for typical Azure Storage account key length (88 characters)
        if self.config.debug:
            print(f"DEBUG: Account key length: {len(account_key)}")
            print(f"DEBUG: Account key ends with: ...{account_key[-10:]}")
        if len(account_key) != 88:
            print(f"WARNING: AccountKey length is {len(account_key)}. Azure Storage account keys are typically 88 characters long.")

        try:
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
                raise StorageError(
                    "Invalid account key format. Please check your AZURE_STORAGE_CONNECTION_STRING in .env file. "
                    "Make sure the AccountKey part is correct and consider regenerating it from the Azure portal."
                )
            raise
        
        blob_url = f"https://{account_name}.blob.core.windows.net/{self.container_name}/{quote(blob_name)}"
        return f"{blob_url}?{sas_token}"
    
    def delete_blob(self, blob_name: str) -> bool:
        """
        Delete a blob from storage
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            blob_client.delete_blob()
            
            if self.config.log_cleanup:
                print(f"Deleted blob: {blob_name}")
            
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
        Returns (successful_deletions, failed_deletions)
        """
        if not self.uploaded_blobs:
            return 0, 0
        
        print(f"\nCleaning up {len(self.uploaded_blobs)} temporary file(s) from Azure...")
        successful = 0
        failed = 0
        
        for blob_name in self.uploaded_blobs.copy():
            if self.delete_blob(blob_name):
                successful += 1
            else:
                failed += 1
        
        if self.config.log_cleanup:
            print(f"Cleanup completed: {successful} deleted, {failed} failed")
        
        return successful, failed

    def is_url(self, path: str) -> bool:
        """
        Check if a path is a URL (http/https)
        """
        return path.startswith(('http://', 'https://'))
