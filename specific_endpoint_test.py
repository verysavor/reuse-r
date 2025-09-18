#!/usr/bin/env python3
"""
Test specific endpoints mentioned in the review request
"""

import requests
import json
import time

def test_specific_endpoints():
    base_url = "https://ecdsa-vulncheck.preview.emergentagent.com/api"
    
    print("🔍 Testing Specific Endpoints from Review Request")
    print("=" * 60)
    
    # Test 1: POST /api/scan/start with specific config
    print("1. Testing POST /api/scan/start with specific config...")
    scan_config = {
        "start_block": 252474,
        "end_block": 252474,
        "address_types": ["legacy", "segwit"]
    }
    
    response = requests.post(f"{base_url}/scan/start", json=scan_config)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        scan_id = data.get('scan_id')
        print(f"   ✅ Scan started successfully: {scan_id}")
        
        # Test 2: GET /api/scan/progress/{scan_id}
        print(f"\n2. Testing GET /api/scan/progress/{scan_id}...")
        
        # Monitor for a few iterations
        for i in range(5):
            time.sleep(3)
            progress_response = requests.get(f"{base_url}/scan/progress/{scan_id}")
            print(f"   Status: {progress_response.status_code}")
            
            if progress_response.status_code == 200:
                progress_data = progress_response.json()
                
                # Check required fields from review request
                required_fields = [
                    'status', 'current_block', 'total_blocks', 
                    'blocks_processed', 'progress_percentage'
                ]
                
                print(f"   Iteration {i+1}:")
                print(f"     Status: {progress_data.get('status')}")
                print(f"     Current Block: {progress_data.get('current_block')}")
                print(f"     Total Blocks: {progress_data.get('total_blocks')}")
                print(f"     Blocks Scanned: {progress_data.get('blocks_scanned')}")  # Note: API uses 'blocks_scanned' not 'blocks_processed'
                print(f"     Progress %: {progress_data.get('progress_percentage')}")
                print(f"     Logs Count: {len(progress_data.get('logs', []))}")
                
                # Check if scan is complete
                if progress_data.get('status') in ['completed', 'failed']:
                    print(f"   ✅ Scan completed with status: {progress_data.get('status')}")
                    break
            else:
                print(f"   ❌ Failed to get progress: {progress_response.status_code}")
                break
        
        print(f"\n3. Final progress data structure:")
        final_response = requests.get(f"{base_url}/scan/progress/{scan_id}")
        if final_response.status_code == 200:
            final_data = final_response.json()
            print(json.dumps(final_data, indent=2, default=str))
        
    else:
        print(f"   ❌ Failed to start scan: {response.status_code}")
        print(f"   Error: {response.text}")

if __name__ == "__main__":
    test_specific_endpoints()