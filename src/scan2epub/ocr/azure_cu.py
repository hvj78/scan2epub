import os
import time
import requests
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

class PDFOCRProcessor:
    """
    Processes PDF files using Azure AI Content Understanding for OCR.
    Extracts structured text (paragraphs, lines, words) from PDF documents.
    """
    def __init__(self, debug_mode: bool = False, debug_dir: Optional[Path] = None):
        self.endpoint = os.getenv("AZURE_CU_ENDPOINT")
        self.api_key = os.getenv("AZURE_CU_API_KEY")
        self.api_version = "2025-05-01-preview"  # Current API version for Content Understanding
        self.analyzer_id = "prebuilt-documentAnalyzer"  # Using the prebuilt document analyzer
        self.debug_mode = debug_mode
        self.debug_dir = debug_dir

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
        json_data = {"url": pdf_path}
        
        try:
            response = requests.post(analyze_url, headers=self.headers, json=json_data)
            response.raise_for_status()  # Raise an exception for HTTP errors
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
        max_retries = 60  # Increased retries for async operation
        retry_delay = 2   # Lower delay per user request
        
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
                    elapsed_s = (attempt + 1) * retry_delay
                    print(f"Analysis status: {status}. Retrying in {retry_delay} seconds (attempt {attempt + 1}/{max_retries}, elapsed {elapsed_s}s)...")
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

        if self.debug_mode and self.debug_dir:
            debug_file_path = self.debug_dir / "azure_cu_result.json"
            with open(debug_file_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"🔍 DEBUG: Azure Content Understanding result saved to: {debug_file_path}")

        return result
                        
    def extract_text_from_ocr_result(self, analyze_result: Dict[str, Any]) -> str:
        """
        Extracts and reconstructs text content from the Content Understanding AnalyzeResult object,
        prioritizing markdown content.
        """
        full_text = []
        contents = analyze_result.get("contents", [])
        if contents:
            for content_item in contents:
                markdown_content = content_item.get("markdown")
                if markdown_content:
                    full_text.append(markdown_content)
        return "\n\n".join(full_text)
