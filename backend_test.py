import requests
import sys
import time
import json
import os
from datetime import datetime
from pathlib import Path

class BitcoinScannerCriticalTester:
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
        self.critical_issues_found = []
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

    def test_progress_tracking_critical(self):
        """CRITICAL TEST: Progress tracking failure diagnosis"""
        print(f"\n🔍 CRITICAL TEST: Progress Tracking Failure Diagnosis...")
        
        # Test with the exact small range mentioned in review request
        scan_config = {
            "start_block": 252474,
            "end_block": 252476,  # Small 3-block range for progress testing
            "address_types": ["legacy", "segwit"]
        }
        
        success, response = self.run_test(
            "Start Small Range Scan (Progress Test)",
            "POST",
            "scan/start",
            200,
            data=scan_config
        )
        
        if success and 'scan_id' in response:
            progress_scan_id = response['scan_id']
            print(f"   Progress test scan ID: {progress_scan_id}")
            
            # Monitor progress every 2 seconds for detailed tracking
            start_time = time.time()
            max_wait = 30  # 30 seconds should be enough for 3 blocks
            progress_updates = []
            
            print(f"   📊 Monitoring progress updates every 2 seconds...")
            
            while time.time() - start_time < max_wait:
                success_progress, progress_response = self.run_test(
                    "Progress Update Check",
                    "GET",
                    f"scan/progress/{progress_scan_id}",
                    200
                )
                
                if success_progress:
                    status = progress_response.get('status', 'unknown')
                    progress = progress_response.get('progress_percentage', 0)
                    blocks_scanned = progress_response.get('blocks_scanned', 0)
                    current_block = progress_response.get('current_block', 0)
                    blocks_per_minute = progress_response.get('blocks_per_minute', 0)
                    
                    progress_update = {
                        'time': time.time() - start_time,
                        'status': status,
                        'progress': progress,
                        'blocks_scanned': blocks_scanned,
                        'current_block': current_block,
                        'blocks_per_minute': blocks_per_minute
                    }
                    progress_updates.append(progress_update)
                    
                    print(f"   [{progress_update['time']:.1f}s] Status: {status}, Progress: {progress:.1f}%, Blocks: {blocks_scanned}, Current: {current_block}, Speed: {blocks_per_minute:.1f}/min")
                    
                    if status in ['completed', 'failed']:
                        break
                
                time.sleep(2)
            
            # Analyze progress tracking
            print(f"\n   📈 Progress Analysis:")
            print(f"      Total updates captured: {len(progress_updates)}")
            
            if len(progress_updates) == 0:
                self.critical_issues_found.append("No progress updates received")
                print(f"   ❌ CRITICAL ISSUE: No progress updates received")
                return False
            
            # Check if progress is stuck at 0%
            stuck_at_zero = all(update['progress'] == 0 for update in progress_updates)
            if stuck_at_zero:
                self.critical_issues_found.append("Progress stuck at 0% - matches reported issue")
                print(f"   ❌ CRITICAL ISSUE: Progress stuck at 0% - matches reported issue")
                return False
            
            # Check if blocks_scanned is stuck at 0
            blocks_stuck_at_zero = all(update['blocks_scanned'] == 0 for update in progress_updates)
            if blocks_stuck_at_zero:
                self.critical_issues_found.append("Blocks scanned stuck at 0 - matches reported issue")
                print(f"   ❌ CRITICAL ISSUE: Blocks scanned stuck at 0 - matches reported issue")
                return False
            
            # Check for progress movement
            final_progress = progress_updates[-1]['progress']
            final_blocks = progress_updates[-1]['blocks_scanned']
            
            if final_progress > 0 and final_blocks > 0:
                print(f"   ✅ Progress tracking working - reached {final_progress:.1f}% with {final_blocks} blocks")
                return True
            else:
                self.critical_issues_found.append("Progress tracking failure confirmed")
                print(f"   ❌ CRITICAL ISSUE: Progress tracking failure confirmed")
                return False
        else:
            self.critical_issues_found.append("Failed to start progress tracking test scan")
            print(f"   ❌ Failed to start progress tracking test scan")
            return False

    def test_api_timeout_diagnosis(self):
        """CRITICAL TEST: API timeout and failure diagnosis"""
        print(f"\n🔍 CRITICAL TEST: API Timeout and Failure Diagnosis...")
        
        # Test individual API endpoints to identify which ones are failing
        api_tests = []
        
        # Test multiple rapid requests to trigger potential API failures
        print(f"   Testing API reliability with rapid requests...")
        
        for i in range(10):  # Test 10 rapid requests
            start_time = time.time()
            success, response = self.run_test(
                f"API Reliability Test #{i+1}",
                "GET",
                "current-height",
                200,
                timeout=10  # Shorter timeout to catch timeouts faster
            )
            end_time = time.time()
            
            api_tests.append({
                'test_num': i+1,
                'success': success,
                'response_time': end_time - start_time,
                'timed_out': end_time - start_time >= 10
            })
            
            if not success:
                print(f"   ⚠️  API test {i+1} failed")
            
            time.sleep(0.5)  # Small delay between requests
        
        # Analyze API performance
        successful_requests = sum(1 for test in api_tests if test['success'])
        failed_requests = len(api_tests) - successful_requests
        timeout_requests = sum(1 for test in api_tests if test['timed_out'])
        avg_response_time = sum(test['response_time'] for test in api_tests) / len(api_tests)
        
        print(f"\n   📊 API Performance Analysis:")
        print(f"      Successful requests: {successful_requests}/10 ({successful_requests*10}%)")
        print(f"      Failed requests: {failed_requests}/10 ({failed_requests*10}%)")
        print(f"      Timeout requests: {timeout_requests}/10 ({timeout_requests*10}%)")
        print(f"      Average response time: {avg_response_time:.2f}s")
        
        # Check for the reported ~30% failure rate
        failure_rate = failed_requests / len(api_tests) * 100
        if failure_rate >= 25:  # 25% or higher failure rate
            self.critical_issues_found.append(f"High API failure rate ({failure_rate:.1f}%) - matches reported issue")
            print(f"   ❌ CRITICAL ISSUE: High API failure rate ({failure_rate:.1f}%) - matches reported issue")
            return False
        elif timeout_requests >= 3:  # 30% or more timeouts
            self.critical_issues_found.append("High timeout rate - 'All APIs timed out' issue confirmed")
            print(f"   ❌ CRITICAL ISSUE: High timeout rate - 'All APIs timed out' issue confirmed")
            return False
        elif successful_requests >= 8:  # 80% or better success rate
            print(f"   ✅ API reliability good - {successful_requests}/10 successful")
            return True
        else:
            self.critical_issues_found.append(f"Moderate API issues detected - {failure_rate:.1f}% failure rate")
            print(f"   ⚠️  Moderate API issues detected - {failure_rate:.1f}% failure rate")
            return False

    def test_large_block_range_issue(self):
        """CRITICAL TEST: Large block range result display issue"""
        print(f"\n🔍 CRITICAL TEST: Large Block Range Result Display Issue...")
        
        # Test the exact range mentioned in the review request
        scan_config = {
            "start_block": 252474,
            "end_block": 253000,  # Large range that reportedly shows no results
            "address_types": ["legacy", "segwit"]
        }
        
        success, response = self.run_test(
            "Start Large Range Scan (252474-253000)",
            "POST",
            "scan/start",
            200,
            data=scan_config
        )
        
        if success and 'scan_id' in response:
            large_scan_id = response['scan_id']
            print(f"   Large range scan ID: {large_scan_id}")
            
            # Wait a reasonable time to see if scan starts properly
            print(f"   ⏳ Monitoring large range scan for 30 seconds...")
            
            start_time = time.time()
            max_wait = 30
            
            while time.time() - start_time < max_wait:
                success_progress, progress_response = self.run_test(
                    "Large Range Progress Check",
                    "GET",
                    f"scan/progress/{large_scan_id}",
                    200
                )
                
                if success_progress:
                    status = progress_response.get('status', 'unknown')
                    progress = progress_response.get('progress_percentage', 0)
                    blocks_scanned = progress_response.get('blocks_scanned', 0)
                    signatures_found = progress_response.get('signatures_found', 0)
                    
                    print(f"   [{time.time() - start_time:.1f}s] Status: {status}, Progress: {progress:.1f}%, Blocks: {blocks_scanned}, Signatures: {signatures_found}")
                    
                    # Check if scan is making progress
                    if blocks_scanned > 0 or progress > 0:
                        print(f"   ✅ Large range scan is making progress")
                        
                        # Stop the scan to avoid long wait
                        stop_success, _ = self.run_test(
                            "Stop Large Range Scan",
                            "POST",
                            f"scan/stop/{large_scan_id}",
                            200
                        )
                        
                        if stop_success:
                            print(f"   ✅ Large range scan stopped successfully")
                            return True
                        else:
                            print(f"   ⚠️  Could not stop large range scan")
                            return False
                    
                    if status in ['completed', 'failed']:
                        break
                
                time.sleep(3)
            
            # Check final status
            success_final, final_response = self.run_test(
                "Large Range Final Check",
                "GET",
                f"scan/progress/{large_scan_id}",
                200
            )
            
            if success_final:
                final_status = final_response.get('status', 'unknown')
                final_progress = final_response.get('progress_percentage', 0)
                final_blocks = final_response.get('blocks_scanned', 0)
                
                if final_blocks == 0 and final_progress == 0:
                    self.critical_issues_found.append("Large range scan shows no progress - matches reported issue")
                    print(f"   ❌ CRITICAL ISSUE: Large range scan shows no progress - matches reported issue")
                    return False
                else:
                    print(f"   ✅ Large range scan working - progress: {final_progress:.1f}%, blocks: {final_blocks}")
                    return True
            else:
                self.critical_issues_found.append("Could not get final status for large range scan")
                print(f"   ❌ Could not get final status for large range scan")
                return False
        else:
            self.critical_issues_found.append("Failed to start large range scan")
            print(f"   ❌ Failed to start large range scan")
            return False

    def test_coroutine_handling(self):
        """CRITICAL TEST: Coroutine handling bug diagnosis"""
        print(f"\n🔍 CRITICAL TEST: Coroutine Handling Bug Diagnosis...")
        
        # Start multiple scans simultaneously to test async handling
        scan_configs = [
            {"start_block": 1, "end_block": 3, "address_types": ["legacy"]},
            {"start_block": 4, "end_block": 6, "address_types": ["segwit"]},
            {"start_block": 7, "end_block": 9, "address_types": ["legacy", "segwit"]}
        ]
        
        scan_ids = []
        
        print(f"   Starting multiple concurrent scans to test coroutine handling...")
        
        for i, config in enumerate(scan_configs):
            success, response = self.run_test(
                f"Concurrent Scan #{i+1}",
                "POST",
                "scan/start",
                200,
                data=config
            )
            
            if success and 'scan_id' in response:
                scan_ids.append(response['scan_id'])
                print(f"   Concurrent scan {i+1} started: {response['scan_id']}")
            else:
                self.critical_issues_found.append(f"Failed to start concurrent scan {i+1}")
                print(f"   ❌ Failed to start concurrent scan {i+1}")
                return False
            
            time.sleep(1)  # Small delay between starts
        
        if len(scan_ids) != 3:
            self.critical_issues_found.append("Could not start all concurrent scans")
            print(f"   ❌ Could not start all concurrent scans")
            return False
        
        # Monitor all scans for coroutine errors
        print(f"   📊 Monitoring {len(scan_ids)} concurrent scans for coroutine issues...")
        
        start_time = time.time()
        max_wait = 45
        all_scans_ok = True
        
        while time.time() - start_time < max_wait:
            active_scans = 0
            
            for i, scan_id in enumerate(scan_ids):
                success_progress, progress_response = self.run_test(
                    f"Concurrent Scan {i+1} Progress",
                    "GET",
                    f"scan/progress/{scan_id}",
                    200
                )
                
                if success_progress:
                    status = progress_response.get('status', 'unknown')
                    progress = progress_response.get('progress_percentage', 0)
                    
                    if status == 'running':
                        active_scans += 1
                    elif status == 'failed':
                        self.critical_issues_found.append(f"Concurrent scan {i+1} failed - possible coroutine issue")
                        print(f"   ❌ Concurrent scan {i+1} failed - possible coroutine issue")
                        all_scans_ok = False
                else:
                    self.critical_issues_found.append(f"Could not get progress for concurrent scan {i+1} - possible coroutine issue")
                    print(f"   ❌ Could not get progress for concurrent scan {i+1} - possible coroutine issue")
                    all_scans_ok = False
            
            if active_scans == 0:  # All scans completed or failed
                break
            
            print(f"   [{time.time() - start_time:.1f}s] Active scans: {active_scans}")
            time.sleep(5)
        
        if all_scans_ok:
            print(f"   ✅ Coroutine handling working - all concurrent scans processed without errors")
            return True
        else:
            self.critical_issues_found.append("Coroutine handling problems detected")
            print(f"   ❌ CRITICAL ISSUE: Coroutine handling problems detected")
            return False

    def test_known_working_block_252474(self):
        """Test the known working block 252474 that should contain reused R-values"""
        print(f"\n🔍 Testing Known Working Block 252474...")
        
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
                        self.critical_issues_found.append("No R-value reuse detected in block 252474 (expected to find some)")
                        print(f"   ⚠️  No R-value reuse detected in block 252474 (expected to find some)")
                        return False
                else:
                    self.critical_issues_found.append("Failed to get results for block 252474 scan")
                    print(f"   ❌ Failed to get results for block 252474 scan")
                    return False
            else:
                self.critical_issues_found.append("Block 252474 scan did not complete in time")
                print(f"   ❌ Block 252474 scan did not complete in time")
                return False
        else:
            self.critical_issues_found.append("Failed to start scan for block 252474")
            print(f"   ❌ Failed to start scan for block 252474")
            return False

    def test_basic_endpoints(self):
        """Test basic API endpoints"""
        print(f"\n🔍 Testing Basic API Endpoints...")
        
        # Health check
        health_success, _ = self.run_test("Health Check", "GET", "health", 200)
        
        # Current height
        height_success, height_response = self.run_test("Current Height", "GET", "current-height", 200)
        
        # List scans
        list_success, _ = self.run_test("List Scans", "GET", "scan/list", 200)
        
        if health_success and height_success and list_success:
            if 'height' in height_response:
                print(f"   ✅ Basic endpoints working - Current height: {height_response['height']}")
                return True
        
        self.critical_issues_found.append("Basic API endpoints failing")
        print(f"   ❌ Basic API endpoints failing")
        return False

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
    print("🚀 Starting Bitcoin Reused-R Scanner CRITICAL ISSUE DIAGNOSIS")
    print("🎯 Focus: Progress Tracking, API Failures, Result Display, Coroutine Bugs")
    print("=" * 70)
    
    tester = BitcoinScannerCriticalTester()
    
    # CRITICAL TESTS - prioritizing the specific issues mentioned in review request
    critical_tests = [
        ("Basic API Endpoints", tester.test_basic_endpoints),
        ("CRITICAL: Progress Tracking Failure", tester.test_progress_tracking_critical),
        ("CRITICAL: API Timeout Diagnosis", tester.test_api_timeout_diagnosis),
        ("CRITICAL: Large Block Range Issue", tester.test_large_block_range_issue),
        ("CRITICAL: Coroutine Handling", tester.test_coroutine_handling),
        ("Known Working Block 252474", tester.test_known_working_block_252474),
    ]
    
    # Run all tests
    for test_name, test_func in critical_tests:
        try:
            print(f"\n{'='*50}")
            print(f"🧪 Running: {test_name}")
            print(f"{'='*50}")
            test_func()
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            tester.critical_issues_found.append(f"Test {test_name} crashed: {e}")
            import traceback
            traceback.print_exc()
    
    # Print final results
    print("\n" + "=" * 70)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    # Print critical issues summary
    if tester.critical_issues_found:
        print(f"\n🚨 CRITICAL ISSUES FOUND ({len(tester.critical_issues_found)}):")
        for i, issue in enumerate(tester.critical_issues_found, 1):
            print(f"   {i}. {issue}")
    else:
        print(f"\n✅ No critical issues detected")
    
    if tester.tests_passed == tester.tests_run and not tester.critical_issues_found:
        print("🎉 All tests passed and no critical issues found!")
        return 0
    else:
        failed = tester.tests_run - tester.tests_passed
        print(f"⚠️  {failed} test(s) failed and {len(tester.critical_issues_found)} critical issues found")
        print("❌ Critical failures detected - requires investigation")
        return 1

if __name__ == "__main__":
    sys.exit(main())