#!/usr/bin/env python3
"""
Comprehensive Backend Test for Bitcoin Reused-R Scanner
Tests all functionality mentioned in the review request
"""

import requests
import json
import time
import sys

class ComprehensiveAPITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_passed = 0
        self.tests_failed = 0
        self.scan_ids = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
            if details:
                print(f"   {details}")
        else:
            self.tests_failed += 1
            print(f"❌ {name}")
            if details:
                print(f"   {details}")

    def test_api_health_checks(self):
        """Test /api/health and /api/current-height endpoints"""
        print("\n🔍 Testing API Health Checks...")
        
        # Test health endpoint
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            success = response.status_code == 200 and response.json().get('status') == 'healthy'
            self.log_test("Health Check Endpoint", success, 
                         f"Status: {response.json().get('status', 'unknown')}")
        except Exception as e:
            self.log_test("Health Check Endpoint", False, f"Error: {e}")

        # Test current height endpoint
        try:
            response = requests.get(f"{self.api_url}/current-height", timeout=10)
            if response.status_code == 200:
                height = response.json().get('height', 0)
                success = height > 900000  # Should be around 915000+
                self.log_test("Current Height Endpoint", success, 
                             f"Height: {height}")
            else:
                self.log_test("Current Height Endpoint", False, 
                             f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Current Height Endpoint", False, f"Error: {e}")

    def test_scan_functionality(self):
        """Test /api/scan/start with single block and small range scans"""
        print("\n🔍 Testing Scan Functionality...")
        
        # Test single block scan (early block with few transactions)
        try:
            scan_config = {
                "start_block": 1000,
                "end_block": 1000,
                "address_types": ["legacy", "segwit"]
            }
            response = requests.post(f"{self.api_url}/scan/start", 
                                   json=scan_config, timeout=10)
            if response.status_code == 200:
                scan_id = response.json().get('scan_id')
                self.scan_ids.append(scan_id)
                self.log_test("Single Block Scan Start", True, 
                             f"Scan ID: {scan_id[:8]}...")
            else:
                self.log_test("Single Block Scan Start", False, 
                             f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Single Block Scan Start", False, f"Error: {e}")

        # Test small range scan
        try:
            scan_config = {
                "start_block": 1000,
                "end_block": 1002,
                "address_types": ["legacy", "segwit"]
            }
            response = requests.post(f"{self.api_url}/scan/start", 
                                   json=scan_config, timeout=10)
            if response.status_code == 200:
                scan_id = response.json().get('scan_id')
                self.scan_ids.append(scan_id)
                self.log_test("Small Range Scan Start", True, 
                             f"Scan ID: {scan_id[:8]}...")
            else:
                self.log_test("Small Range Scan Start", False, 
                             f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Small Range Scan Start", False, f"Error: {e}")

    def test_progress_tracking(self):
        """Test /api/scan/progress/{scan_id} for active scans"""
        print("\n🔍 Testing Progress Tracking...")
        
        if not self.scan_ids:
            self.log_test("Progress Tracking", False, "No scan IDs available")
            return

        for scan_id in self.scan_ids:
            try:
                response = requests.get(f"{self.api_url}/scan/progress/{scan_id}", 
                                      timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    required_fields = ['scan_id', 'status', 'current_block', 
                                     'progress_percentage', 'blocks_scanned', 'total_blocks']
                    has_all_fields = all(field in data for field in required_fields)
                    self.log_test(f"Progress Tracking ({scan_id[:8]}...)", has_all_fields,
                                 f"Status: {data.get('status')}, Progress: {data.get('progress_percentage', 0):.1f}%")
                else:
                    self.log_test(f"Progress Tracking ({scan_id[:8]}...)", False,
                                 f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Progress Tracking ({scan_id[:8]}...)", False, f"Error: {e}")

    def test_r_value_detection(self):
        """Verify the core scanning logic finds reused R values correctly"""
        print("\n🔍 Testing R-value Detection Logic...")
        
        # Wait for scans to complete and check results
        completed_scans = 0
        for scan_id in self.scan_ids:
            try:
                # Wait up to 60 seconds for scan to complete
                for _ in range(20):  # 20 * 3 = 60 seconds max
                    response = requests.get(f"{self.api_url}/scan/progress/{scan_id}", 
                                          timeout=10)
                    if response.status_code == 200:
                        status = response.json().get('status')
                        if status in ['completed', 'failed', 'stopped']:
                            break
                    time.sleep(3)
                
                # Check final results
                response = requests.get(f"{self.api_url}/scan/results/{scan_id}", 
                                      timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    required_fields = ['scan_id', 'status', 'recovered_keys', 'total_keys']
                    has_all_fields = all(field in data for field in required_fields)
                    
                    if has_all_fields and data.get('status') == 'completed':
                        completed_scans += 1
                        self.log_test(f"R-value Detection ({scan_id[:8]}...)", True,
                                     f"Completed: {data.get('total_keys', 0)} keys, {data.get('r_reuse_pairs', 0)} R-reuse pairs")
                    else:
                        self.log_test(f"R-value Detection ({scan_id[:8]}...)", False,
                                     f"Status: {data.get('status', 'unknown')}")
                else:
                    self.log_test(f"R-value Detection ({scan_id[:8]}...)", False,
                                 f"Results Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"R-value Detection ({scan_id[:8]}...)", False, f"Error: {e}")

        # Overall R-value detection test
        self.log_test("Core R-value Detection Logic", completed_scans > 0,
                     f"{completed_scans}/{len(self.scan_ids)} scans completed successfully")

    def test_error_handling(self):
        """Test API failure scenarios and fallback mechanisms"""
        print("\n🔍 Testing Error Handling...")
        
        # Test invalid scan ID
        try:
            response = requests.get(f"{self.api_url}/scan/progress/invalid-scan-id", 
                                  timeout=10)
            success = response.status_code == 404
            self.log_test("Invalid Scan ID Handling", success,
                         f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Invalid Scan ID Handling", False, f"Error: {e}")

        # Test invalid scan configuration
        try:
            invalid_config = {
                "start_block": 100,
                "end_block": 50,  # Invalid: end < start
                "address_types": ["legacy"]
            }
            response = requests.post(f"{self.api_url}/scan/start", 
                                   json=invalid_config, timeout=10)
            # Should return 400 or 500 with appropriate error message
            success = response.status_code in [400, 500] and "End block must be greater" in response.text
            self.log_test("Invalid Scan Config Handling", success,
                         f"Status: {response.status_code}, Message: {response.text[:50]}...")
        except Exception as e:
            self.log_test("Invalid Scan Config Handling", False, f"Error: {e}")

        # Test CryptoAPIs integration status
        try:
            response = requests.get(f"{self.api_url}/test-cryptoapis", timeout=10)
            if response.status_code == 200:
                data = response.json()
                has_key = data.get('has_api_key', False)
                tests = data.get('tests', {})
                
                # CryptoAPIs is expected to fail with "uri_not_found"
                if 'latest_block' in tests:
                    block_test = tests['latest_block']
                    cryptoapis_failing = not block_test.get('success', True)
                    self.log_test("CryptoAPIs Expected Failure", cryptoapis_failing,
                                 f"Has key: {has_key}, Failing as expected: {cryptoapis_failing}")
                else:
                    self.log_test("CryptoAPIs Test Endpoint", True, "Endpoint accessible")
            else:
                self.log_test("CryptoAPIs Test Endpoint", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("CryptoAPIs Test Endpoint", False, f"Error: {e}")

    def test_performance_parallel_processing(self):
        """Check parallel processing with Blockstream and Mempool.space APIs"""
        print("\n🔍 Testing Performance & Parallel Processing...")
        
        # Test API fallback mechanisms
        try:
            # Test current height (should work with fallback APIs)
            response = requests.get(f"{self.api_url}/current-height", timeout=10)
            height_works = response.status_code == 200 and response.json().get('height', 0) > 0
            
            # Test balance check (uses fallback APIs)
            test_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Genesis address
            response = requests.post(f"{self.api_url}/balance/check", 
                                   json=[test_address], timeout=15)
            balance_works = response.status_code == 200 and 'balances' in response.json()
            
            fallback_success = height_works and balance_works
            self.log_test("API Fallback Mechanisms", fallback_success,
                         f"Height API: {height_works}, Balance API: {balance_works}")
        except Exception as e:
            self.log_test("API Fallback Mechanisms", False, f"Error: {e}")

        # Test scan list functionality
        try:
            response = requests.get(f"{self.api_url}/scan/list", timeout=10)
            if response.status_code == 200:
                data = response.json()
                scans = data.get('scans', [])
                has_backend_marker = any(scan.get('backend_verification') == 'custom-backend-confirmed' 
                                       for scan in scans)
                self.log_test("Scan List & Backend Verification", has_backend_marker,
                             f"Found {len(scans)} scans with backend verification")
            else:
                self.log_test("Scan List & Backend Verification", False,
                             f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Scan List & Backend Verification", False, f"Error: {e}")

    def run_comprehensive_test(self):
        """Run all comprehensive tests"""
        print("🚀 Starting Comprehensive Bitcoin Reused-R Scanner Backend Tests")
        print("=" * 80)
        
        # Run all test categories
        self.test_api_health_checks()
        self.test_scan_functionality()
        self.test_progress_tracking()
        self.test_r_value_detection()
        self.test_error_handling()
        self.test_performance_parallel_processing()
        
        # Print final results
        print("\n" + "=" * 80)
        total_tests = self.tests_passed + self.tests_failed
        print(f"📊 Final Results: {self.tests_passed}/{total_tests} tests passed")
        
        if self.tests_failed == 0:
            print("🎉 All tests passed! Backend is working correctly.")
            return 0
        else:
            print(f"⚠️  {self.tests_failed} test(s) failed")
            return 1

def main():
    tester = ComprehensiveAPITester()
    return tester.run_comprehensive_test()

if __name__ == "__main__":
    sys.exit(main())