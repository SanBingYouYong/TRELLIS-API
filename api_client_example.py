#!/usr/bin/env python3
"""
TRELLIS Text-to-3D API Client Example

This script demonstrates how to interact with the TRELLIS Text-to-3D API.
It shows how to send requests, check status, and download generated files.

Usage:
    python api_client_example.py --prompt "A futuristic robot" --api-url http://localhost:8000
"""

import requests
import time
import json
import argparse
from pathlib import Path
from typing import Optional


class TrellisAPIClient:
    """Client for interacting with the TRELLIS Text-to-3D API"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url.rstrip('/')
        
    def health_check(self) -> dict:
        """Check if the API is healthy and ready"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Health check failed: {e}")
    
    def generate_3d(
        self,
        prompt: str,
        seed: Optional[int] = None,
        formats: list = None,
        **kwargs
    ) -> dict:
        """
        Generate 3D asset from text prompt
        
        Args:
            prompt: Text description of the 3D object
            seed: Random seed for reproducible generation
            formats: List of output formats ['mesh', 'gaussian']
            **kwargs: Additional generation parameters
            
        Returns:
            Dictionary with generation results
        """
        if formats is None:
            formats = ["mesh", "gaussian"]
            
        payload = {
            "prompt": prompt,
            "formats": formats,
            **kwargs
        }
        
        if seed is not None:
            payload["seed"] = seed
            
        try:
            print(f"Sending generation request for: '{prompt}'")
            response = requests.post(
                f"{self.api_url}/generate", 
                json=payload,
                timeout=600  # 10 minutes timeout for generation
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Generation request failed: {e}")
    
    def download_file(self, job_id: str, filename: str, output_dir: str = ".") -> str:
        """
        Download a generated file
        
        Args:
            job_id: Job ID from generation response
            filename: Name of the file to download
            output_dir: Directory to save the file
            
        Returns:
            Path to the downloaded file
        """
        output_path = Path(output_dir) / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            response = requests.get(
                f"{self.api_url}/files/{job_id}/{filename}",
                stream=True,
                timeout=60
            )
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            print(f"Downloaded: {output_path}")
            return str(output_path)
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Download failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="TRELLIS Text-to-3D API Client Example")
    parser.add_argument("--prompt", type=str, required=True, help="Text description of 3D object")
    parser.add_argument("--api-url", type=str, default="http://localhost:8000", help="API base URL")
    parser.add_argument("--seed", type=int, help="Random seed for reproducible generation")
    parser.add_argument("--output-dir", type=str, default="./generated", help="Output directory for files")
    parser.add_argument("--formats", nargs="+", default=["mesh", "gaussian"], help="Output formats")
    parser.add_argument("--no-video", action="store_true", help="Skip video generation")
    
    # Generation parameters
    parser.add_argument("--ss-steps", type=int, default=12, help="Sparse structure sampling steps")
    parser.add_argument("--ss-cfg", type=float, default=7.5, help="Sparse structure CFG strength")
    parser.add_argument("--slat-steps", type=int, default=12, help="Structured latent sampling steps")
    parser.add_argument("--slat-cfg", type=float, default=7.5, help="Structured latent CFG strength")
    
    args = parser.parse_args()
    
    # Create client
    client = TrellisAPIClient(args.api_url)
    
    try:
        # Check API health
        print("Checking API health...")
        health = client.health_check()
        print(f"API Status: {health['status']}")
        print(f"GPU Available: {health['gpu_available']}")
        print(f"Model Loaded: {health['model_loaded']}")
        
        if health['status'] != 'healthy':
            print("API is not healthy. Please check the server.")
            return
        
        # Prepare generation parameters
        generation_params = {
            "ss_steps": args.ss_steps,
            "ss_cfg_strength": args.ss_cfg,
            "slat_steps": args.slat_steps,
            "slat_cfg_strength": args.slat_cfg,
            "generate_video": not args.no_video,
            "formats": args.formats
        }
        
        # Generate 3D asset
        print(f"\nGenerating 3D asset...")
        print(f"This may take several minutes depending on the complexity...")
        
        result = client.generate_3d(
            prompt=args.prompt,
            seed=args.seed,
            **generation_params
        )
        
        print(f"\nGeneration completed!")
        print(f"Job ID: {result['job_id']}")
        print(f"Status: {result['status']}")
        print(f"Generation Time: {result['generation_time_seconds']:.2f} seconds")
        print(f"Seed Used: {result['seed']}")
        
        # Download generated files
        if result['files']:
            print(f"\nDownloading generated files...")
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            for file_type, file_url in result['files'].items():
                filename = file_url.split('/')[-1]
                try:
                    downloaded_path = client.download_file(
                        result['job_id'], 
                        filename, 
                        args.output_dir
                    )
                    print(f"  {file_type}: {downloaded_path}")
                except Exception as e:
                    print(f"  Failed to download {file_type}: {e}")
        
        # Print model information
        if result.get('model_info'):
            print(f"\nModel Information:")
            for key, value in result['model_info'].items():
                print(f"  {key}: {value}")
        
        print(f"\nGeneration complete! Files saved to: {args.output_dir}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
