"""API client with pagination and retry logic."""

import time
import sys
import requests
from typing import List, Dict, Any, Optional

class APIClient:
    """HTTP client for CxOne API with pagination and retry support."""
    
    def __init__(self, base_url, auth_manager, config, debug=False, debug_logger=None):
        """Initialize the API client.
        
        Args:
            base_url (str): The base URL for API requests
            auth_manager (AuthManager): Authentication manager instance
            config (Config): Configuration instance
            debug (bool): Enable debug output
            debug_logger (DebugLogger, optional): Debug logger instance
        """
        self.base_url = base_url
        self.auth = auth_manager
        self.config = config
        self.debug = debug
        self.logger = debug_logger
    
    def get_paginated(self, endpoint, params=None, max_results=None):
        """Fetch all results from a paginated endpoint.
        
        Args:
            endpoint (str): API endpoint path
            params (dict, optional): Query parameters
            max_results (int, optional): Maximum number of results to fetch
            
        Returns:
            list: All results from paginated responses
        """
        all_results = []
        offset = 0
        limit = self.config.page_size
        params = params or {}
        
        while True:
            # Add pagination parameters
            page_params = params.copy()
            page_params['limit'] = limit
            page_params['offset'] = offset
            
            if self.debug:
                print(f"  Fetching {endpoint} (offset={offset}, limit={limit})...")
            
            response_data = self.get(endpoint, params=page_params)
            
            if not response_data:
                break
            
            # Handle different response formats
            if isinstance(response_data, dict):
                # Check for common pagination patterns
                if 'projects' in response_data:
                    results = response_data.get('projects', [])
                elif 'scans' in response_data:
                    results = response_data.get('scans', [])
                elif 'branches' in response_data:
                    results = response_data.get('branches', [])
                elif 'items' in response_data:
                    results = response_data.get('items', [])
                else:
                    # Assume the dict itself is the result
                    results = [response_data]
            elif isinstance(response_data, list):
                results = response_data
            else:
                break
            
            if not results:
                break
            
            all_results.extend(results)
            
            if self.debug:
                print(f"    Retrieved {len(results)} items (total: {len(all_results)})")
            
            # Check if we've reached max results
            if max_results and len(all_results) >= max_results:
                all_results = all_results[:max_results]
                break
            
            # Check if we've reached the end
            if len(results) < limit:
                break
            
            offset += limit
        
        return all_results
    
    def get(self, endpoint, params=None):
        """Make a GET request with retry logic.
        
        Args:
            endpoint (str): API endpoint path
            params (dict, optional): Query parameters
            
        Returns:
            dict or list: Response data
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.config.max_retries):
            try:
                headers = self.auth.get_headers()
                response = requests.get(
                    url, 
                    headers=headers, 
                    params=params,
                    timeout=self.config.request_timeout
                )
                
                if response.status_code == 429:
                    # Rate limited - wait longer
                    wait_time = 30
                    if self.debug:
                        print(f"    Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout:
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    if self.debug:
                        print(f"    Timeout. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    if self.debug:
                        print(f"    Request timed out after {self.config.max_retries} attempts")
                    return None
                    
            except requests.exceptions.RequestException as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    if self.debug:
                        print(f"    Error: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    if self.debug:
                        print(f"    Request failed after {self.config.max_retries} attempts: {e}")
                    return None
        
        return None
    
    def post(self, endpoint, data=None, json_data=None):
        """Make a POST request with retry logic.
        
        Args:
            endpoint (str): API endpoint path
            data (dict, optional): Form data
            json_data (dict, optional): JSON data
            
        Returns:
            dict: Response data
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.config.max_retries):
            try:
                headers = self.auth.get_headers()
                response = requests.post(
                    url,
                    headers=headers,
                    data=data,
                    json=json_data,
                    timeout=self.config.request_timeout
                )
                
                if response.status_code == 429:
                    # Rate limited - wait longer
                    wait_time = 30
                    if self.debug:
                        print(f"    Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    if self.debug:
                        print(f"    Error: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    if self.debug:
                        print(f"    Request failed after {self.config.max_retries} attempts: {e}")
                    return None
        
        return None
    
    def post_sca_export(self, endpoint, json_data=None):
        """Make a POST request for SCA export with specific headers.
        
        Args:
            endpoint (str): API endpoint path
            json_data (dict, optional): JSON data
            
        Returns:
            dict: Response data
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.config.max_retries):
            try:
                # Get base headers and add SCA-specific headers
                headers = self.auth.get_headers()
                headers['Accept'] = 'application/json; version=1.0'
                
                response = requests.post(
                    url,
                    headers=headers,
                    json=json_data,
                    timeout=self.config.request_timeout
                )
                
                if response.status_code == 429:
                    # Rate limited - wait longer
                    wait_time = 30
                    if self.debug:
                        print(f"    Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    if self.debug:
                        print(f"    Error: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    if self.debug:
                        print(f"    Request failed after {self.config.max_retries} attempts: {e}")
                    return None
        
        return None
    
    def download_file(self, endpoint, output_path):
        """Download a file from an endpoint.
        
        Args:
            endpoint (str): API endpoint path
            output_path (str): Where to save the file
            
        Returns:
            bool: True if successful, False otherwise
        """
        import os
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            headers = self.auth.get_headers()
            response = requests.get(
                url,
                headers=headers,
                timeout=self.config.request_timeout,
                stream=True
            )
            response.raise_for_status()
            
            # Write file safely
            with open(output_path, 'wb') as f:  # nosec - path is controlled by FileManager
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
            
        except Exception as e:
            if self.debug:
                print(f"    Failed to download file: {e}")
            return False

