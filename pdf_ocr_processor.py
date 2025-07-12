import os
import time
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class PDFOCRProcessor:
    """
    Processes PDF files using Azure AI Content Understanding for OCR.
    Extracts structured text (paragraphs, lines, words) from PDF documents.
    """
    def __init__(self):
        self.endpoint = os.getenv("AZURE_CU_ENDPOINT")
        self.api_key = os.getenv("AZURE_CU_API_KEY")
        self.api_version = "2025-05-01-preview" # Current API version for Content Understanding
        self.analyzer_id = "prebuilt-documentAnalyzer" # Using the prebuilt document analyzer

        if not self.endpoint or not self.api_key:
            raise ValueError("AZURE_CU_ENDPOINT and AZURE_CU_API_KEY must be set in environment variables.")
            
        self.headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
    def _send_analyze_request(self, pdf_path: str) -> str:
        """
        Sends the analyze request to Azure AI Content Understanding and returns the operation ID.
        """
        analyze_url = f"{self.endpoint}/contentunderstanding/analyzers/{self.analyzer_id}:analyze?api-version={self.api_version}"
        
        # For local files, we need to upload them or provide a publicly accessible URL.
        # For simplicity, this example assumes a publicly accessible URL or a local file
        # that can be read as bytes. If you need to upload, consider Azure Blob Storage.
        
        json_data = {"url": pdf_path}
        
        try:
            response = requests.post(analyze_url, headers=self.headers, json=json_data)
            response.raise_for_status() # Raise an exception for HTTP errors
            
            operation_id = response.json().get("id")
            if not operation_id:
                raise ValueError("Operation ID not found in the analyze response.")
            return operation_id
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error sending analyze request: {e}")

    def _get_analyze_result(self, operation_id: str) -> Dict[str, Any]:
        """
        Polls for the analysis result using the operation ID.
        """
        result_url = f"{self.endpoint}/contentunderstanding/analyzerResults/{operation_id}?api-version={self.api_version}"
        
        max_retries = 60 # Increased retries for async operation
        retry_delay = 10 # Increased delay
        
        for attempt in range(max_retries):
            try:
                response = requests.get(result_url, headers=self.headers)
                response.raise_for_status()
                
                result = response.json()
                status = result.get("status")
                
                if status == "Succeeded":
                    return result.get("result")
                elif status == "Failed":
                    raise Exception(f"Content Understanding analysis failed: {result.get('error', 'Unknown error')}")
                elif status in ["Running", "NotStarted"]:
                    print(f"Analysis status: {status}. Retrying in {retry_delay} seconds (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Unexpected analysis status: {status}")
            except requests.exceptions.RequestException as e:
                print(f"Error polling for result (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise
        raise TimeoutError("Content Understanding analysis timed out.")

    def process_pdf(self, pdf_url: str) -> Dict[str, Any]:
        """
        Analyzes a PDF file (via URL) using Azure AI Content Understanding and returns the OCR results.
        
        Args:
            pdf_url (str): A publicly accessible URL to the PDF file.
        
        Returns:
            Dict[str, Any]: The JSON result from the Content Understanding API.
        """
        print(f"Starting OCR processing for PDF URL: {pdf_url}")
        
        operation_id = self._send_analyze_request(pdf_url)
        print(f"Analysis initiated with Operation ID: {operation_id}")
        
        result = self._get_analyze_result(operation_id)
        print(f"OCR processing completed for {pdf_url}")
        return result
                        
    def extract_text_from_ocr_result(self, analyze_result: Dict[str, Any]) -> str:
        """
        Extracts and reconstructs text content from the Content Understanding AnalyzeResult object,
        prioritizing markdown content.
        """
        full_text = []
        
        # Content Understanding returns a 'contents' array, each item can have 'markdown'
        contents = analyze_result.get("contents", [])
        
        if contents:
            for content_item in contents:
                markdown_content = content_item.get("markdown")
                if markdown_content:
                    full_text.append(markdown_content)
                # Optionally, you can also extract from 'paragraphs' or 'lines' if markdown is not sufficient
                # For now, markdown is preferred as it's higher level.
        
        return "\n\n".join(full_text)

if __name__ == "__main__":
    # Example Usage (requires a .env file with AZURE_CU_ENDPOINT and AZURE_CU_API_KEY)
    # and a publicly accessible URL to a sample PDF.
    
    # IMPORTANT: Replace with a real publicly accessible PDF URL for testing.
    # Example: "https://github.com/Azure-Samples/azure-ai-content-understanding-python/raw/refs/heads/main/data/invoice.pdf"
    sample_pdf_url = "YOUR_PUBLICLY_ACCESSIBLE_PDF_URL_HERE" 

    if sample_pdf_url == "YOUR_PUBLICLY_ACCESSIBLE_PDF_URL_HERE":
        print("Please update 'sample_pdf_url' in pdf_ocr_processor.py with a real publicly accessible PDF URL for testing.")
        print("You can use a sample from Azure: https://github.com/Azure-Samples/azure-ai-content-understanding-python/raw/refs/heads/main/data/invoice.pdf")
        exit(1)

    try:
        processor = PDFOCRProcessor()
        ocr_result = processor.process_pdf(sample_pdf_url)
        
        # Print extracted text
        extracted_text = processor.extract_text_from_ocr_result(ocr_result)
        print("\n--- Extracted Text ---")
        print(extracted_text)
        
        # You can also inspect the full OCR result object
        # print("\n--- Full OCR Result (JSON) ---")
        # import json
        # print(json.dumps(ocr_result, indent=2))
        
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
