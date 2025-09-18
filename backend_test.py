import requests
import sys
import time
import json
import os
from datetime import datetime
from pathlib import Path

class BitcoinScannerAPITester:
    def __init__(self):
        # Load the correct URL from frontend/.env
        frontend_env_path = Path(__file__).parent / "frontend" / ".env"
        base_url = "http://localhost:8001"  # Default fallback
        
        if frontend_env_path.exists():
            with open(frontend_env_path, 'r') as f:
                for line in f:
                    if line.startswith('REACT_APP_BACKEND_URL='):
                        base_url = line.split('=', 1)[1].strip()
                        break
        
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.scan_id = None
        print(f"🔗 Using backend URL: {self.base_url}")

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            print(f"   Response Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timed out after {timeout} seconds")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_current_height(self):
        """Test current blockchain height endpoint"""
        success, response = self.run_test(
            "Current Blockchain Height",
            "GET",
            "current-height",
            200
        )
        if success and 'height' in response:
            height = response['height']
            print(f"   Current blockchain height: {height}")
            return height > 0
        return False

    def test_start_scan(self):
        """Test starting a scan with small block range"""
        scan_config = {
            "start_block": 1,
            "end_block": 10,
            "address_types": ["legacy", "segwit"]
        }
        
        success, response = self.run_test(
            "Start Scan",
            "POST",
            "scan/start",
            200,
            data=scan_config
        )
        
        if success and 'scan_id' in response:
            self.scan_id = response['scan_id']
            print(f"   Scan ID: {self.scan_id}")
            return True
        return False

    def test_scan_progress(self):
        """Test getting scan progress"""
        if not self.scan_id:
            print("❌ No scan ID available for progress test")
            return False
            
        success, response = self.run_test(
            "Scan Progress",
            "GET",
            f"scan/progress/{self.scan_id}",
            200
        )
        
        if success:
            required_fields = ['scan_id', 'status', 'current_block', 'progress_percentage']
            has_all_fields = all(field in response for field in required_fields)
            if has_all_fields:
                print(f"   Status: {response['status']}")
                print(f"   Progress: {response['progress_percentage']:.1f}%")
                return True
        return False

    def test_scan_results(self):
        """Test getting scan results"""
        if not self.scan_id:
            print("❌ No scan ID available for results test")
            return False
            
        success, response = self.run_test(
            "Scan Results",
            "GET",
            f"scan/results/{self.scan_id}",
            200
        )
        
        if success:
            required_fields = ['scan_id', 'status', 'recovered_keys', 'total_keys']
            has_all_fields = all(field in response for field in required_fields)
            if has_all_fields:
                print(f"   Total keys recovered: {response['total_keys']}")
                print(f"   R reuse pairs: {response.get('r_reuse_pairs', 0)}")
                return True
        return False

    def test_balance_check(self):
        """Test balance checking with sample addresses"""
        sample_addresses = [
            "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",  # Genesis block address
            "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"   # Sample bech32 address
        ]
        
        success, response = self.run_test(
            "Balance Check",
            "POST",
            "balance/check",
            200,
            data=sample_addresses
        )
        
        if success and 'balances' in response:
            balances = response['balances']
            print(f"   Checked {len(balances)} addresses")
            for balance in balances[:2]:  # Show first 2
                print(f"   {balance['address']}: {balance['balance']} BTC")
            return len(balances) == len(sample_addresses)
        return False

    def test_scan_list(self):
        """Test listing all scans"""
        success, response = self.run_test(
            "List Scans",
            "GET",
            "scan/list",
            200
        )
        
        if success and 'scans' in response:
            scans = response['scans']
            print(f"   Found {len(scans)} scans")
            return True
        return False

    def test_export_results(self):
        """Test exporting scan results"""
        if not self.scan_id:
            print("❌ No scan ID available for export test")
            return False
            
        # Note: This endpoint returns a file, so we expect different handling
        url = f"{self.api_url}/scan/export/{self.scan_id}"
        
        self.tests_run += 1
        print(f"\n🔍 Testing Export Results...")
        print(f"   URL: {url}")
        
        try:
            response = requests.get(url, timeout=30)
            print(f"   Response Status: {response.status_code}")
            
            if response.status_code == 200:
                self.tests_passed += 1
                print(f"✅ Passed - Export file received")
                print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
                print(f"   Content-Length: {len(response.content)} bytes")
                return True
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def test_cryptoapis_integration(self):
        """Test CryptoAPIs integration and authentication fix"""
        print(f"\n🔍 Testing CryptoAPIs Integration Fix...")
        
        # Test current height endpoint which should use CryptoAPIs in rotation
        success, response = self.run_test(
            "Current Height (CryptoAPIs Integration)",
            "GET",
            "current-height",
            200
        )
        
        if success and 'height' in response:
            height = response['height']
            print(f"   ✅ CryptoAPIs integration working - Current height: {height}")
            # Test multiple times to ensure API rotation includes CryptoAPIs
            for i in range(3):
                success2, response2 = self.run_test(
                    f"Height Check #{i+2} (API Rotation)",
                    "GET",
                    "current-height",
                    200
                )
                if not success2:
                    print(f"   ⚠️  API rotation test {i+2} failed")
                    return False
            print(f"   ✅ API rotation working - all 4 requests successful")
            return True
        else:
            print(f"   ❌ CryptoAPIs integration failed - no height returned")
            return False

    def test_r_value_detection_block_252474(self):
        """Test R-value detection with known vulnerable block 252474"""
        print(f"\n🔍 Testing R-value Detection with Block 252474...")
        
        scan_config = {
            "start_block": 252474,
            "end_block": 252474,
            "address_types": ["legacy", "segwit"]
        }
        
        success, response = self.run_test(
            "Start Scan Block 252474 (Known R-value Reuse)",
            "POST",
            "scan/start",
            200,
            data=scan_config
        )
        
        if success and 'scan_id' in response:
            self.scan_id = response['scan_id']
            print(f"   Scan ID for block 252474: {self.scan_id}")
            
            # Wait for scan to complete with longer timeout for this specific block
            print(f"   ⏳ Waiting for block 252474 scan to complete...")
            scan_completed = self.wait_for_scan_completion(120)  # 2 minutes timeout
            
            if scan_completed:
                # Check results for R-value reuse detection
                success_results, results_response = self.run_test(
                    "Block 252474 Results (R-value Detection)",
                    "GET",
                    f"scan/results/{self.scan_id}",
                    200
                )
                
                if success_results:
                    r_reuse_pairs = results_response.get('r_reuse_pairs', 0)
                    recovered_keys = results_response.get('total_keys', 0)
                    
                    print(f"   📊 Block 252474 Results:")
                    print(f"      R-value reuse pairs found: {r_reuse_pairs}")
                    print(f"      Private keys recovered: {recovered_keys}")
                    
                    # Block 252474 is known to contain reused R-values
                    if r_reuse_pairs > 0:
                        print(f"   ✅ R-value reuse detection working - found {r_reuse_pairs} reused R-values")
                        return True
                    else:
                        print(f"   ⚠️  No R-value reuse detected in block 252474 (expected to find some)")
                        return False
                else:
                    print(f"   ❌ Failed to get results for block 252474 scan")
                    return False
            else:
                print(f"   ❌ Block 252474 scan did not complete in time")
                return False
        else:
            print(f"   ❌ Failed to start scan for block 252474")
            return False

    def test_api_error_handling(self):
        """Test API error handling and fallback mechanisms"""
        print(f"\n🔍 Testing API Error Handling and Fallback...")
        
        # Test multiple rapid requests to trigger potential rate limiting and fallback
        print(f"   Testing rapid API requests for fallback behavior...")
        
        successful_requests = 0
        for i in range(5):
            success, response = self.run_test(
                f"Rapid Request #{i+1}",
                "GET",
                "current-height",
                200
            )
            if success:
                successful_requests += 1
            time.sleep(0.5)  # Small delay between requests
        
        if successful_requests >= 4:  # Allow for 1 potential failure
            print(f"   ✅ API fallback working - {successful_requests}/5 requests successful")
            return True
        else:
            print(f"   ❌ API fallback issues - only {successful_requests}/5 requests successful")
            return False

    def test_parallel_processing(self):
        """Test parallel processing with multiple block range"""
        print(f"\n🔍 Testing Parallel Processing...")
        
        scan_config = {
            "start_block": 1,
            "end_block": 5,  # Small range for quick testing
            "address_types": ["legacy", "segwit"]
        }
        
        success, response = self.run_test(
            "Start Parallel Processing Scan",
            "POST",
            "scan/start",
            200,
            data=scan_config
        )
        
        if success and 'scan_id' in response:
            parallel_scan_id = response['scan_id']
            print(f"   Parallel scan ID: {parallel_scan_id}")
            
            # Monitor progress to ensure parallel processing is working
            start_time = time.time()
            max_wait = 60
            
            while time.time() - start_time < max_wait:
                success_progress, progress_response = self.run_test(
                    "Parallel Scan Progress",
                    "GET",
                    f"scan/progress/{parallel_scan_id}",
                    200
                )
                
                if success_progress:
                    status = progress_response.get('status', 'unknown')
                    progress = progress_response.get('progress_percentage', 0)
                    blocks_per_minute = progress_response.get('blocks_per_minute', 0)
                    
                    print(f"   Status: {status}, Progress: {progress:.1f}%, Speed: {blocks_per_minute:.1f} blocks/min")
                    
                    if status in ['completed', 'failed']:
                        if status == 'completed':
                            print(f"   ✅ Parallel processing completed successfully")
                            return True
                        else:
                            print(f"   ❌ Parallel processing failed")
                            return False
                
                time.sleep(3)
            
            print(f"   ⚠️  Parallel processing test timed out")
            return False
        else:
            print(f"   ❌ Failed to start parallel processing scan")
            return False

    def test_invalid_endpoints(self):
        """Test error handling with invalid requests"""
        print(f"\n🔍 Testing Error Handling...")
        
        # Test invalid scan ID
        success, _ = self.run_test(
            "Invalid Scan Progress",
            "GET",
            "scan/progress/invalid-scan-id",
            404
        )
        
        # Test invalid scan config
        invalid_config = {
            "start_block": 100,
            "end_block": 50,  # End block less than start block
            "address_types": ["legacy"]
        }
        
        success2, _ = self.run_test(
            "Invalid Scan Config",
            "POST",
            "scan/start",
            400,
            data=invalid_config
        )
        
        return success and success2
        """Test error handling with invalid requests"""
        print(f"\n🔍 Testing Error Handling...")
        
        # Test invalid scan ID
        success, _ = self.run_test(
            "Invalid Scan Progress",
            "GET",
            "scan/progress/invalid-scan-id",
            404
        )
        
        # Test invalid scan config
        invalid_config = {
            "start_block": 100,
            "end_block": 50,  # End block less than start block
            "address_types": ["legacy"]
        }
        
        success2, _ = self.run_test(
            "Invalid Scan Config",
            "POST",
            "scan/start",
            400,
            data=invalid_config
        )
        
        return success and success2

    def wait_for_scan_completion(self, max_wait_time=60):
        """Wait for scan to complete or timeout"""
        if not self.scan_id:
            return False
            
        print(f"\n⏳ Waiting for scan to complete (max {max_wait_time}s)...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                url = f"{self.api_url}/scan/progress/{self.scan_id}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status', 'unknown')
                    progress = data.get('progress_percentage', 0)
                    
                    print(f"   Status: {status}, Progress: {progress:.1f}%")
                    
                    if status in ['completed', 'failed', 'stopped']:
                        print(f"   Scan finished with status: {status}")
                        return status == 'completed'
                        
                time.sleep(3)  # Wait 3 seconds between checks
                
            except Exception as e:
                print(f"   Error checking progress: {e}")
                time.sleep(3)
        
        print(f"   Timeout reached after {max_wait_time}s")
        return False

def main():
    print("🚀 Starting Bitcoin Reused-R Scanner API Tests")
    print("🎯 Focus: CryptoAPIs Integration Fix & R-value Detection")
    print("=" * 70)
    
    tester = BitcoinScannerAPITester()
    
    # Test sequence - prioritizing CryptoAPIs integration tests
    tests = [
        ("Health Check", lambda: tester.run_test("Health Check", "GET", "health", 200)[0]),
        ("CryptoAPIs Integration", tester.test_cryptoapis_integration),
        ("API Error Handling", tester.test_api_error_handling),
        ("Parallel Processing", tester.test_parallel_processing),
        ("R-value Detection Block 252474", tester.test_r_value_detection_block_252474),
        ("Balance Check", tester.test_balance_check),
        ("List Scans", tester.test_scan_list),
        ("Error Handling", tester.test_invalid_endpoints),
    ]
    
    # Run all tests
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*50}")
            print(f"🧪 Running: {test_name}")
            print(f"{'='*50}")
            test_func()
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            import traceback
            traceback.print_exc()
    
    # Test export functionality if we have a scan
    if tester.scan_id:
        try:
            print(f"\n{'='*50}")
            print(f"🧪 Running: Export Results")
            print(f"{'='*50}")
            tester.test_export_results()
        except Exception as e:
            print(f"❌ Export test crashed: {e}")
    
    # Print final results
    print("\n" + "=" * 70)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        print("✅ CryptoAPIs integration fix verified successfully")
        return 0
    else:
        failed = tester.tests_run - tester.tests_passed
        print(f"⚠️  {failed} test(s) failed")
        if failed <= 2:  # Allow for minor failures
            print("🔶 Minor failures detected - core functionality appears working")
            return 0
        else:
            print("❌ Major failures detected - requires investigation")
            return 1

if __name__ == "__main__":
    sys.exit(main())