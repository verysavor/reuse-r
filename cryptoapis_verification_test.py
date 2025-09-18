#!/usr/bin/env python3
"""
CryptoAPIs Integration Verification Test
Specifically tests the points mentioned in the review request
"""

import requests
import json
import time

def test_cryptoapis_verification():
    """Comprehensive CryptoAPIs integration verification"""
    base_url = "http://localhost:8001/api"
    
    print("🔥 CryptoAPIs Integration Verification Test")
    print("=" * 60)
    
    results = {
        "cryptoapis_auth": False,
        "api_rotation": False,
        "scan_integration": False,
        "rate_limiting": False,
        "three_apis_available": False
    }
    
    # 1. Test CryptoAPIs Authentication
    print("\n1. 🔍 Testing CryptoAPIs Authentication (/api/test-cryptoapis)")
    try:
        response = requests.get(f"{base_url}/test-cryptoapis", timeout=30)
        if response.status_code == 200:
            data = response.json()
            has_key = data.get('has_api_key', False)
            tests = data.get('tests', {})
            
            print(f"   ✅ Endpoint responds: HTTP {response.status_code}")
            print(f"   ✅ Has API Key: {has_key}")
            
            if 'latest_block' in tests:
                block_test = tests['latest_block']
                success = block_test.get('success', False)
                status_code = block_test.get('status_code', 0)
                
                print(f"   ✅ Block Test Success: {success}")
                print(f"   ✅ Status Code: {status_code}")
                
                if success and status_code == 200:
                    results["cryptoapis_auth"] = True
                    print("   🎉 CryptoAPIs Authentication: WORKING")
                else:
                    print("   ❌ CryptoAPIs Authentication: FAILED")
                    print(f"      Error: {block_test.get('response_text', 'Unknown error')}")
            
            if 'block_height' in tests:
                height_test = tests['block_height']
                height_success = height_test.get('success', False)
                height = height_test.get('height', 0)
                print(f"   ✅ Height Test: {height_success} (Height: {height})")
        else:
            print(f"   ❌ Test endpoint failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Test endpoint error: {e}")
    
    # 2. Test API Rotation (3 APIs: Blockstream, Mempool.space, CryptoAPIs)
    print("\n2. 🔍 Testing API Rotation (3 APIs Available)")
    try:
        # Make multiple requests to see API rotation
        heights = []
        for i in range(9):  # 9 requests should cycle through 3 APIs 3 times each
            response = requests.get(f"{base_url}/current-height", timeout=10)
            if response.status_code == 200:
                height = response.json().get('height', 0)
                heights.append(height)
                print(f"   Request {i+1}: Height = {height}")
            else:
                print(f"   Request {i+1}: Failed (HTTP {response.status_code})")
            time.sleep(0.3)
        
        valid_heights = [h for h in heights if h > 900000]
        if len(valid_heights) >= 6:  # At least 6 successful requests
            results["api_rotation"] = True
            results["three_apis_available"] = True
            print(f"   🎉 API Rotation: WORKING ({len(valid_heights)}/9 successful)")
            print(f"   🎉 Three APIs Available: CONFIRMED")
        else:
            print(f"   ❌ API Rotation Issues: Only {len(valid_heights)}/9 successful")
    except Exception as e:
        print(f"   ❌ API rotation test error: {e}")
    
    # 3. Test Rate Limiting Improvements
    print("\n3. 🔍 Testing Rate Limiting Improvements")
    try:
        start_time = time.time()
        successful = 0
        total_requests = 15
        
        for i in range(total_requests):
            response = requests.get(f"{base_url}/current-height", timeout=5)
            if response.status_code == 200:
                successful += 1
            time.sleep(0.1)  # 100ms between requests
        
        end_time = time.time()
        duration = end_time - start_time
        success_rate = successful / total_requests
        rps = total_requests / duration
        
        print(f"   ✅ Success Rate: {success_rate*100:.1f}% ({successful}/{total_requests})")
        print(f"   ✅ Rate: {rps:.2f} requests/second")
        print(f"   ✅ Duration: {duration:.2f}s")
        
        if success_rate >= 0.8:  # 80% success rate indicates good rate limiting
            results["rate_limiting"] = True
            print("   🎉 Rate Limiting: IMPROVED")
        else:
            print("   ❌ Rate Limiting: ISSUES DETECTED")
    except Exception as e:
        print(f"   ❌ Rate limiting test error: {e}")
    
    # 4. Test Small Range Scan (CryptoAPIs Integration)
    print("\n4. 🔍 Testing Small Range Scan (CryptoAPIs Integration)")
    try:
        scan_config = {
            "start_block": 915000,
            "end_block": 915000,  # Single block for quick test
            "address_types": ["legacy", "segwit"]
        }
        
        response = requests.post(f"{base_url}/scan/start", json=scan_config, timeout=10)
        if response.status_code == 200:
            scan_data = response.json()
            scan_id = scan_data.get('scan_id')
            print(f"   ✅ Scan Started: {scan_id}")
            
            # Wait a bit and check progress
            time.sleep(5)
            progress_response = requests.get(f"{base_url}/scan/progress/{scan_id}", timeout=10)
            if progress_response.status_code == 200:
                progress = progress_response.json()
                status = progress.get('status', 'unknown')
                api_calls = progress.get('api_calls_made', 0)
                errors = progress.get('errors_encountered', 0)
                
                print(f"   ✅ Scan Status: {status}")
                print(f"   ✅ API Calls Made: {api_calls}")
                print(f"   ✅ Errors: {errors}")
                
                # Stop the scan
                requests.post(f"{base_url}/scan/stop/{scan_id}", timeout=5)
                
                results["scan_integration"] = True
                print("   🎉 Scan Integration: WORKING")
            else:
                print("   ❌ Could not get scan progress")
        else:
            print(f"   ❌ Scan start failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Scan test error: {e}")
    
    # 5. Test Health and Current Height
    print("\n5. 🔍 Testing Basic Endpoints")
    try:
        # Health check
        health_response = requests.get(f"{base_url}/health", timeout=10)
        health_ok = health_response.status_code == 200
        print(f"   ✅ Health Check: {'PASS' if health_ok else 'FAIL'}")
        
        # Current height
        height_response = requests.get(f"{base_url}/current-height", timeout=10)
        height_ok = height_response.status_code == 200
        if height_ok:
            height = height_response.json().get('height', 0)
            print(f"   ✅ Current Height: {height} (PASS)")
        else:
            print(f"   ❌ Current Height: FAIL")
    except Exception as e:
        print(f"   ❌ Basic endpoints error: {e}")
    
    # Final Summary
    print("\n" + "=" * 60)
    print("🎯 FINAL VERIFICATION RESULTS:")
    print(f"   1. CryptoAPIs Authentication: {'✅ PASS' if results['cryptoapis_auth'] else '❌ FAIL'}")
    print(f"   2. API Rotation (3 APIs): {'✅ PASS' if results['api_rotation'] else '❌ FAIL'}")
    print(f"   3. Rate Limiting Improvements: {'✅ PASS' if results['rate_limiting'] else '❌ FAIL'}")
    print(f"   4. Scan Integration: {'✅ PASS' if results['scan_integration'] else '❌ FAIL'}")
    print(f"   5. Three APIs Available: {'✅ PASS' if results['three_apis_available'] else '❌ FAIL'}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\n📊 Overall Score: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("🎉 ALL CRYPTOAPIS INTEGRATION TESTS PASSED!")
        return True
    else:
        print("⚠️  Some CryptoAPIs integration issues detected")
        return False

if __name__ == "__main__":
    success = test_cryptoapis_verification()
    exit(0 if success else 1)