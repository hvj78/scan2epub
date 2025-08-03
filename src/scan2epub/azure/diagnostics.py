"""
Azure Configuration Tester for scan2epub

Comprehensive testing suite to validate all Azure services and configurations
needed by the scan2epub application. Provides detailed diagnostics and
recommendations for troubleshooting.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Optional

import requests
import openai
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from azure.core.exceptions import AzureError
from dotenv import load_dotenv  # CLI should call load_dotenv(), but keep here for stand-alone use
import binascii  # For binascii.Error handling

from scan2epub.config_manager import ConfigManager  # Using INI-based config under package


class Colors:
    """ANSI color codes for console output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


class AzureConfigTester:
    """Comprehensive Azure configuration testing suite"""
    
    def __init__(self):
        """Initialize the tester"""
        self.config = None
        self.test_results = []
        self.warnings = []
        self.errors = []
        
        # Test file content for blob storage testing
        self.test_content = b"This is a test file for scan2epub Azure configuration validation."
        
    def print_header(self, text: str):
        """Print a formatted header"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
        print("=" * len(text))
    
    def print_step(self, step: str, total: str, description: str):
        """Print a test step header"""
        print(f"\n{Colors.BOLD}[{step}/{total}] {description}{Colors.END}")
    
    def print_success(self, message: str):
        """Print a success message"""
        print(f"{Colors.GREEN}✓{Colors.END} {message}")
    
    def print_error(self, message: str):
        """Print an error message"""
        print(f"{Colors.RED}✗{Colors.END} {message}")
        self.errors.append(message)
    
    def print_warning(self, message: str):
        """Print a warning message"""
        print(f"{Colors.YELLOW}⚠{Colors.END} {message}")
        self.warnings.append(message)
    
    def print_info(self, message: str):
        """Print an info message"""
        print(f"{Colors.BLUE}ℹ{Colors.END} {message}")
    
    def print_recommendation(self, message: str):
        """Print a recommendation"""
        print(f"{Colors.YELLOW}💡 Recommendation:{Colors.END} {message}")
    
    def test_environment_configuration(self) -> bool:
        """Test environment configuration and .env file"""
        self.print_step("1", "4", "Environment Configuration")
        
        success = True
        
        # Test .env file loading (support stand-alone run)
        try:
            load_dotenv()
            self.print_success(".env file found and loaded")
        except Exception as e:
            self.print_error(f"Failed to load .env file: {str(e)}")
            self.print_recommendation("Ensure .env file exists in the project root directory")
            return False
        
        # Test configuration manager
        try:
            self.config = ConfigManager()
            self.print_success("Configuration manager initialized")
        except Exception as e:
            self.print_error(f"Configuration manager failed: {str(e)}")
            success = False
        
        # Check required environment variables
        required_vars = {
            'AZURE_STORAGE_CONNECTION_STRING': 'Azure Blob Storage connection string',
            'AZURE_CU_API_KEY': 'Azure Content Understanding API key',
            'AZURE_CU_ENDPOINT': 'Azure Content Understanding endpoint',
            'AZURE_OPENAI_API_KEY': 'Azure OpenAI API key',
            'AZURE_OPENAI_ENDPOINT': 'Azure OpenAI endpoint',
            'AZURE_OPENAI_DEPLOYMENT_NAME': 'Azure OpenAI deployment name'
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            value = os.getenv(var)
            if not value:
                missing_vars.append(f"{var} ({description})")
                self.print_error(f"Missing environment variable: {var}")
            else:
                self.print_success(f"{var} is set")
        
        if missing_vars:
            self.print_recommendation("Add missing environment variables to your .env file")
            success = False
        
        # Validate connection string format
        conn_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if conn_string:
            if self._validate_connection_string(conn_string):
                self.print_success("Storage connection string format is valid")
            else:
                self.print_error("Storage connection string format is invalid")
                success = False
        
        return success
    
    def _validate_connection_string(self, conn_string: str) -> bool:
        """Validate Azure Storage connection string format"""
        required_parts = ['DefaultEndpointsProtocol', 'AccountName', 'AccountKey', 'EndpointSuffix']
        parts = conn_string.split(';')
        
        found_parts = set()
        for part in parts:
            if '=' in part:
                key = part.split('=')[0]
                found_parts.add(key)
        
        missing_parts = set(required_parts) - found_parts
        if missing_parts:
            self.print_error(f"Connection string missing parts: {', '.join(missing_parts)}")
            return False
        
        # Check if AccountKey ends with ==
        for part in parts:
            if part.startswith('AccountKey='):
                account_key = part.split('=', 1)[1]
                if not account_key.endswith('=='):
                    self.print_warning("Account key should typically end with '=='")
                break
        
        return True
    
    def test_azure_storage(self) -> bool:
        """Test Azure Blob Storage connectivity and operations"""
        self.print_step("2", "4", "Azure Blob Storage")
        
        conn_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if not conn_string:
            self.print_error("No storage connection string available")
            return False
        
        success = True
        blob_client = None
        test_blob_name = f"test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            # Test connection
            blob_service_client = BlobServiceClient.from_connection_string(conn_string)
            self.print_success("Storage service client created")
            
            # Test container access
            container_name = self.config.blob_container_name if self.config else 'scan2epub-temp'
            container_client = blob_service_client.get_container_client(container_name)
            
            # Check if container exists, create if not
            try:
                if not container_client.exists():
                    container_client.create_container()
                    self.print_success(f"Container '{container_name}' created")
                else:
                    self.print_success(f"Container '{container_name}' exists")
            except AzureError as e:
                if "ContainerAlreadyExists" in str(e):
                    self.print_success(f"Container '{container_name}' exists")
                else:
                    self.print_error(f"Container access failed: {str(e)}")
                    self.print_recommendation("Check if your Azure account has Storage Blob Data Contributor role")
                    success = False
            
            # Test blob upload
            blob_client = blob_service_client.get_blob_client(
                container=container_name,
                blob=test_blob_name
            )
            
            blob_client.upload_blob(self.test_content, overwrite=True)
            self.print_success("Test blob uploaded successfully")
            
            # Test SAS token generation
            account_name = None
            account_key = None
            for part in conn_string.split(';'):
                if part.startswith('AccountName='):
                    account_name = part.split('=', 1)[1]
                elif part.startswith('AccountKey='):
                    account_key = part.split('=', 1)[1]
            
            if account_name and account_key:
                sas_token = generate_blob_sas(
                    account_name=account_name,
                    container_name=container_name,
                    blob_name=test_blob_name,
                    account_key=account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.utcnow() + timedelta(hours=1)
                )
                self.print_success("SAS token generated successfully")
            else:
                self.print_error("Could not extract account credentials for SAS token")
                success = False
            
            # Test blob download
            download_stream = blob_client.download_blob()
            downloaded_content = download_stream.readall()
            if downloaded_content == self.test_content:
                self.print_success("Test blob downloaded and verified")
            else:
                self.print_error("Downloaded content doesn't match uploaded content")
                success = False
            
            # Clean up test blob
            blob_client.delete_blob()
            self.print_success("Test blob cleaned up")
            
        except AzureError as e:
            self.print_error(f"Azure Storage error: {str(e)}")
            if "AuthenticationFailed" in str(e):
                self.print_recommendation("Check your storage account key in the connection string")
            elif "ResourceNotFound" in str(e):
                self.print_recommendation("Verify your storage account name and that it exists")
            elif "Forbidden" in str(e):
                self.print_recommendation("Check firewall settings and IP restrictions on your storage account")
            success = False
        except binascii.Error as e:
            self.print_error(f"Base64 decoding error with account key: {str(e)}")
            self.print_recommendation("Ensure your AZURE_STORAGE_CONNECTION_STRING's AccountKey is correctly Base64 encoded and padded.")
            success = False
        except Exception as e:
            self.print_error(f"Unexpected error: {str(e)}")
            success = False
        
        return success
    
    def test_content_understanding(self) -> bool:
        """Test Azure Content Understanding API"""
        self.print_step("3", "4", "Azure Content Understanding")
        
        api_key = os.getenv('AZURE_CU_API_KEY')
        endpoint = os.getenv('AZURE_CU_ENDPOINT')
        
        if not api_key or not endpoint:
            self.print_error("Content Understanding credentials not available")
            return False
        
        success = True
        
        try:
            # Test endpoint connectivity
            headers = {
                "Ocp-Apim-Subscription-Key": api_key,
                "Content-Type": "application/json"
            }
            
            test_url = f"{endpoint.rstrip('/')}/contentunderstanding/analyzers?api-version=2025-05-01-preview"
            
            response = requests.get(test_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                self.print_success("Content Understanding API endpoint reachable")
                self.print_success("API key authentication successful")
            elif response.status_code == 401:
                self.print_error("Authentication failed - check your API key")
                self.print_recommendation("Verify AZURE_CU_API_KEY in your .env file")
                success = False
            elif response.status_code == 403:
                self.print_error("Access forbidden - check permissions")
                self.print_recommendation("Ensure your API key has proper permissions")
                success = False
            else:
                self.print_warning(f"Unexpected response code: {response.status_code}")
                self.print_info(f"Response: {response.text[:200]}")
            
        except requests.exceptions.ConnectionError:
            self.print_error("Cannot connect to Content Understanding endpoint")
            self.print_recommendation("Check your internet connection and firewall settings")
            success = False
        except requests.exceptions.Timeout:
            self.print_error("Request timeout - endpoint may be slow or unreachable")
            self.print_recommendation("Check network connectivity and try again")
            success = False
        except Exception as e:
            self.print_error(f"Unexpected error: {str(e)}")
            success = False
        
        return success
    
    def test_azure_openai(self) -> bool:
        """Test Azure OpenAI API"""
        self.print_step("4", "4", "Azure OpenAI")
        
        api_key = os.getenv('AZURE_OPENAI_API_KEY')
        endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')
        api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
        
        if not all([api_key, endpoint, deployment_name]):
            self.print_error("Azure OpenAI credentials not complete")
            return False
        
        success = True
        
        try:
            # Initialize Azure OpenAI client
            client = openai.AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=endpoint
            )
            
            self.print_success("Azure OpenAI client initialized")
            
            # Test with a simple completion
            test_messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, this is a test' in exactly those words."}
            ]
            
            response = client.chat.completions.create(
                model=deployment_name,
                messages=test_messages,
                max_tokens=50,
                temperature=0
            )
            
            if response.choices and response.choices[0].message:
                self.print_success("Test completion request successful")
                response_text = response.choices[0].message.content.strip()
                if "Hello" in response_text:
                    self.print_success("Model response validated")
                else:
                    self.print_warning(f"Unexpected response: {response_text}")
            else:
                self.print_error("No response from model")
                success = False
                
        except openai.AuthenticationError:
            self.print_error("Authentication failed - check your API key")
            self.print_recommendation("Verify AZURE_OPENAI_API_KEY in your .env file")
            success = False
        except openai.NotFoundError:
            self.print_error("Deployment not found")
            self.print_recommendation("Check AZURE_OPENAI_DEPLOYMENT_NAME - ensure the deployment exists")
            success = False
        except openai.RateLimitError:
            self.print_warning("Rate limit exceeded - but connection is working")
            self.print_recommendation("Consider upgrading your Azure OpenAI quota")
        except Exception as e:
            self.print_error(f"Unexpected error: {str(e)}")
            if "Connection" in str(e):
                self.print_recommendation("Check your internet connection and firewall settings")
            success = False
        
        return success
    
    def run_all_tests(self) -> bool:
        """Run all configuration tests"""
        self.print_header("Azure Configuration Test Suite for scan2epub")
        
        # Run all tests
        test_results = []
        test_results.append(("Environment Configuration", self.test_environment_configuration()))
        test_results.append(("Azure Blob Storage", self.test_azure_storage()))
        test_results.append(("Azure Content Understanding", self.test_content_understanding()))
        test_results.append(("Azure OpenAI", self.test_azure_openai()))
        
        # Print summary
        self.print_header("Test Summary")
        
        all_passed = True
        for test_name, result in test_results:
            if result:
                self.print_success(f"{test_name}: PASSED")
            else:
                self.print_error(f"{test_name}: FAILED")
                all_passed = False
        
        # Print warnings and errors summary
        if self.warnings:
            print(f"\n{Colors.YELLOW}Warnings ({len(self.warnings)}):{Colors.END}")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
        
        if self.errors:
            print(f"\n{Colors.RED}Errors ({len(self.errors)}):{Colors.END}")
            for error in self.errors:
                print(f"  ✗ {error}")
        
        # Final verdict
        if all_passed:
            self.print_header("🎉 All tests passed! Your Azure configuration is ready.")
            print(f"{Colors.GREEN}You can now use scan2epub with local PDF files.{Colors.END}")
        else:
            self.print_header("❌ Some tests failed. Please fix the issues above.")
            print(f"{Colors.RED}scan2epub may not work properly until these issues are resolved.{Colors.END}")
        
        return all_passed


def main():
    """Main function for running Azure configuration tests"""
    # Allow stand-alone execution
    load_dotenv()
    tester = AzureConfigTester()
    return tester.run_all_tests()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
