import requests
import sys
import time
import json
from datetime import datetime

class BitcoinScannerAPITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.scan_id = None
        self.cryptoapis_working = False
        self.api_rotation_verified = False

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

    def test_health_check(self):
        """Test health check endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )
        if success and 'status' in response:
            status = response['status']
            print(f"   Health status: {status}")
            return status == 'healthy'
        return False

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
            # Expect height to be around 915000+ as mentioned in review request
            return height > 900000
        return False

    def test_cryptoapis_integration(self):
        """Test CryptoAPIs integration status"""
        success, response = self.run_test(
            "CryptoAPIs Integration Test",
            "GET",
            "test-cryptoapis",
            200
        )
        if success:
            has_key = response.get('has_api_key', False)
            tests = response.get('tests', {})
            print(f"   Has API Key: {has_key}")
            
            if 'latest_block' in tests:
                block_test = tests['latest_block']
                print(f"   Latest Block Test Success: {block_test.get('success', False)}")
                print(f"   Status Code: {block_test.get('status_code', 'unknown')}")
                if not block_test.get('success', False):
                    print(f"   Error Response: {block_test.get('response_text', 'No error text')}")
            
            return True  # Test passes if endpoint responds, regardless of CryptoAPIs status
        return False

    def test_start_scan_single_block(self):
        """Test starting a scan with single recent block"""
        scan_config = {
            "start_block": 915000,
            "end_block": 915000,
            "address_types": ["legacy", "segwit"]
        }
        
        success, response = self.run_test(
            "Start Single Block Scan",
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

    def test_start_scan_small_range(self):
        """Test starting a scan with small block range"""
        scan_config = {
            "start_block": 915000,
            "end_block": 915002,
            "address_types": ["legacy", "segwit"]
        }
        
        success, response = self.run_test(
            "Start Small Range Scan",
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

    def test_api_fallback_mechanisms(self):
        """Test that APIs work with fallback to Blockstream/Mempool when CryptoAPIs fails"""
        print(f"\n🔍 Testing API Fallback Mechanisms...")
        
        # Test current height (should work with fallback APIs)
        success1, response1 = self.run_test(
            "Height with Fallback",
            "GET",
            "current-height",
            200
        )
        
        height_works = success1 and response1.get('height', 0) > 0
        
        # Test balance check (uses fallback APIs)
        test_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Genesis address
        success2, response2 = self.run_test(
            "Balance with Fallback",
            "POST",
            "balance/check",
            200,
            data=[test_address]
        )
        
        balance_works = success2 and 'balances' in response2
        
        if height_works and balance_works:
            print("✅ API fallback mechanisms working correctly")
            return True
        else:
            print("❌ API fallback mechanisms not working properly")
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
    print("=" * 60)
    
    tester = BitcoinScannerAPITester()
    
    # Test sequence
    tests = [
        ("Health Check", tester.test_health_check),
        ("Current Height", tester.test_current_height),
        ("CryptoAPIs Integration", tester.test_cryptoapis_integration),
        ("API Fallback Mechanisms", tester.test_api_fallback_mechanisms),
        ("Start Single Block Scan", tester.test_start_scan_single_block),
        ("Scan Progress", tester.test_scan_progress),
        ("List Scans", tester.test_scan_list),
        ("Balance Check", tester.test_balance_check),
        ("Error Handling", tester.test_invalid_endpoints),
    ]
    
    # Run basic tests
    for test_name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
    
    # Wait for scan to complete and test results
    if tester.scan_id:
        scan_completed = tester.wait_for_scan_completion(60)
        if scan_completed:
            tester.test_scan_results()
            tester.test_export_results()
        else:
            print("⚠️  Scan did not complete in time, testing results anyway...")
            tester.test_scan_results()
            tester.test_export_results()
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        failed = tester.tests_run - tester.tests_passed
        print(f"⚠️  {failed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())