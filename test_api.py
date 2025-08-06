#!/usr/bin/env python3
"""
TRELLIS Text-to-3D API Test Script

This script performs basic tests on the TRELLIS Text-to-3D API to verify
that it's working correctly.

Usage:
    python test_api.py --api-url http://localhost:8000
"""

import requests
import time
import argparse
import json
import sys
from pathlib import Path


def test_health_check(api_url: str) -> bool:
    """Test the health check endpoint"""
    print("🏥 Testing health check...")
    try:
        response = requests.get(f"{api_url}/health", timeout=10)
        response.raise_for_status()
        health_data = response.json()
        
        print(f"   Status: {health_data['status']}")
        print(f"   GPU Available: {health_data['gpu_available']}")
        print(f"   Model Loaded: {health_data['model_loaded']}")
        
        if health_data['status'] == 'healthy':
            print("   ✅ Health check passed")
            return True
        else:
            print("   ❌ Health check failed - API not healthy")
            return False
            
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False


def test_root_endpoint(api_url: str) -> bool:
    """Test the root endpoint"""
    print("🏠 Testing root endpoint...")
    try:
        response = requests.get(f"{api_url}/", timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'name' in data and 'TRELLIS' in data['name']:
            print("   ✅ Root endpoint working correctly")
            return True
        else:
            print("   ❌ Root endpoint returned unexpected response")
            return False
            
    except Exception as e:
        print(f"   ❌ Root endpoint test failed: {e}")
        return False


def test_generation_simple(api_url: str) -> bool:
    """Test simple 3D generation"""
    print("🎨 Testing simple 3D generation...")
    print("   (This will take several minutes...)")
    
    payload = {
        "prompt": "A simple red cube",
        "seed": 42,
        "formats": ["mesh"],
        "ss_steps": 6,  # Reduced for faster testing
        "ss_cfg_strength": 5.0,
        "slat_steps": 6,  # Reduced for faster testing  
        "slat_cfg_strength": 5.0,
        "generate_video": False,  # Skip video for faster testing
        "texture_size": 512  # Smaller texture for faster processing
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{api_url}/generate",
            json=payload,
            timeout=300  # 5 minutes timeout
        )
        response.raise_for_status()
        result = response.json()
        generation_time = time.time() - start_time
        
        print(f"   Job ID: {result['job_id']}")
        print(f"   Status: {result['status']}")
        print(f"   Generation Time: {result['generation_time_seconds']:.2f}s")
        print(f"   Total Time: {generation_time:.2f}s")
        print(f"   Files Generated: {list(result['files'].keys())}")
        
        if result['status'] == 'success' and result['files']:
            print("   ✅ Generation test passed")
            return True, result
        else:
            print("   ❌ Generation test failed - no files generated")
            return False, None
            
    except requests.exceptions.Timeout:
        print("   ❌ Generation test failed - timeout (this is normal for CPU-only systems)")
        return False, None
    except Exception as e:
        print(f"   ❌ Generation test failed: {e}")
        return False, None


def test_file_download(api_url: str, result: dict) -> bool:
    """Test file download"""
    print("📥 Testing file download...")
    
    if not result or not result.get('files'):
        print("   ⏭ Skipping - no files to download")
        return True
    
    try:
        # Try to download the first available file
        file_type, file_url = next(iter(result['files'].items()))
        filename = file_url.split('/')[-1]
        job_id = result['job_id']
        
        response = requests.get(
            f"{api_url}/files/{job_id}/{filename}",
            timeout=60
        )
        response.raise_for_status()
        
        # Check if we got some content
        content_length = len(response.content)
        print(f"   Downloaded {file_type}: {filename} ({content_length} bytes)")

        # Save the file to the current directory
        # output_path = Path(filename)
        # output_path.write_bytes(response.content)
        
        if content_length > 0:
            print("   ✅ File download test passed")
            return True
        else:
            print("   ❌ File download test failed - empty file")
            return False
            
    except Exception as e:
        print(f"   ❌ File download test failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="TRELLIS Text-to-3D API Test Script")
    parser.add_argument("--api-url", type=str, default="http://localhost:8000", 
                       help="API base URL")
    parser.add_argument("--skip-generation", action="store_true",
                       help="Skip the generation test (useful for quick checks)")
    
    args = parser.parse_args()
    api_url = args.api_url.rstrip('/')
    
    print("🧪 TRELLIS Text-to-3D API Test Suite")
    print("=" * 50)
    print(f"API URL: {api_url}")
    print()
    
    tests_passed = 0
    total_tests = 4 if not args.skip_generation else 2
    
    # Test 1: Health Check
    if test_health_check(api_url):
        tests_passed += 1
    print()
    
    # Test 2: Root Endpoint
    if test_root_endpoint(api_url):
        tests_passed += 1
    print()
    
    # Test 3: Generation (if not skipped)
    generation_result = None
    if not args.skip_generation:
        success, generation_result = test_generation_simple(api_url)
        if success:
            tests_passed += 1
        print()
        
        # Test 4: File Download
        if test_file_download(api_url, generation_result):
            tests_passed += 1
        print()
    
    # Summary
    print("📊 Test Summary")
    print("=" * 20)
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! API is working correctly.")
        return 0
    else:
        print(f"❌ {total_tests - tests_passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
