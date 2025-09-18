#!/usr/bin/env python3
"""
Comprehensive Scan Progress System Test
Focus: Testing scan progress updates, real-time tracking, log updates, and status transitions
"""

import requests
import sys
import time
import json
from datetime import datetime
import threading

class ScanProgressTester:
    def __init__(self, base_url="https://ecdsa-vulncheck.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.scan_id = None
        self.progress_updates = []
        self.monitoring_active = False
        
    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED")
        else:
            print(f"❌ {name}: FAILED")
        
        if details:
            print(f"   {details}")
        print()

    def make_request(self, method, endpoint, data=None, timeout=30):
        """Make HTTP request to API"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            
            return response
        except Exception as e:
            print(f"Request error: {e}")
            return None

    def test_health_check(self):
        """Verify API is accessible"""
        print("🔍 Testing API Health Check...")
        response = self.make_request('GET', 'health')
        
        if response and response.status_code == 200:
            data = response.json()
            success = data.get('status') == 'healthy'
            self.log_test("API Health Check", success, f"Status: {data.get('status')}")
            return success
        else:
            self.log_test("API Health Check", False, f"HTTP {response.status_code if response else 'No response'}")
            return False

    def start_single_block_scan(self, block_number=252474):
        """Start a single block scan as requested"""
        print(f"🔍 Starting Single Block Scan (Block {block_number})...")
        
        scan_config = {
            "start_block": block_number,
            "end_block": block_number,
            "address_types": ["legacy", "segwit"]
        }
        
        response = self.make_request('POST', 'scan/start', data=scan_config)
        
        if response and response.status_code == 200:
            data = response.json()
            self.scan_id = data.get('scan_id')
            success = bool(self.scan_id)
            self.log_test("Single Block Scan Start", success, f"Scan ID: {self.scan_id}")
            return success
        else:
            error_msg = response.json().get('detail', 'Unknown error') if response else 'No response'
            self.log_test("Single Block Scan Start", False, f"Error: {error_msg}")
            return False

    def start_multi_block_scan(self, start_block=252474, end_block=252476):
        """Start a multi-block scan as requested"""
        print(f"🔍 Starting Multi-Block Scan (Blocks {start_block}-{end_block})...")
        
        scan_config = {
            "start_block": start_block,
            "end_block": end_block,
            "address_types": ["legacy", "segwit"]
        }
        
        response = self.make_request('POST', 'scan/start', data=scan_config)
        
        if response and response.status_code == 200:
            data = response.json()
            self.scan_id = data.get('scan_id')
            success = bool(self.scan_id)
            self.log_test("Multi-Block Scan Start", success, f"Scan ID: {self.scan_id}")
            return success
        else:
            error_msg = response.json().get('detail', 'Unknown error') if response else 'No response'
            self.log_test("Multi-Block Scan Start", False, f"Error: {error_msg}")
            return False

    def get_scan_progress(self):
        """Get current scan progress"""
        if not self.scan_id:
            return None
            
        response = self.make_request('GET', f'scan/progress/{self.scan_id}')
        
        if response and response.status_code == 200:
            return response.json()
        return None

    def monitor_progress_updates(self, duration=60):
        """Monitor progress updates in real-time"""
        print(f"🔍 Monitoring Progress Updates for {duration} seconds...")
        
        self.monitoring_active = True
        start_time = time.time()
        update_count = 0
        
        while self.monitoring_active and (time.time() - start_time) < duration:
            progress = self.get_scan_progress()
            if progress:
                timestamp = datetime.now().isoformat()
                progress['timestamp'] = timestamp
                self.progress_updates.append(progress)
                update_count += 1
                
                print(f"   Update #{update_count}: Status={progress.get('status')}, "
                      f"Progress={progress.get('progress_percentage', 0):.1f}%, "
                      f"Current Block={progress.get('current_block')}, "
                      f"Blocks Scanned={progress.get('blocks_scanned', 0)}")
                
                # Stop monitoring if scan is complete
                if progress.get('status') in ['completed', 'failed', 'stopped']:
                    print(f"   Scan finished with status: {progress.get('status')}")
                    break
            
            time.sleep(2)  # Check every 2 seconds
        
        self.monitoring_active = False
        return update_count

    def test_progress_data_structure(self):
        """Test that progress data contains all required fields"""
        print("🔍 Testing Progress Data Structure...")
        
        progress = self.get_scan_progress()
        if not progress:
            self.log_test("Progress Data Structure", False, "Could not retrieve progress data")
            return False
        
        required_fields = [
            'scan_id', 'status', 'current_block', 'blocks_scanned', 
            'total_blocks', 'progress_percentage', 'logs'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in progress:
                missing_fields.append(field)
        
        success = len(missing_fields) == 0
        details = f"All required fields present" if success else f"Missing fields: {missing_fields}"
        self.log_test("Progress Data Structure", success, details)
        
        if success:
            print(f"   Progress Data: {json.dumps(progress, indent=2, default=str)}")
        
        return success

    def test_log_updates(self):
        """Test that logs are being populated during scan"""
        print("🔍 Testing Log Updates...")
        
        progress = self.get_scan_progress()
        if not progress:
            self.log_test("Log Updates", False, "Could not retrieve progress data")
            return False
        
        logs = progress.get('logs', [])
        success = len(logs) > 0
        
        if success:
            details = f"Found {len(logs)} log entries"
            print(f"   Recent logs:")
            for log in logs[-5:]:  # Show last 5 logs
                timestamp = log.get('timestamp', 'No timestamp')
                level = log.get('level', 'info').upper()
                message = log.get('message', 'No message')
                print(f"     [{timestamp}] {level}: {message}")
        else:
            details = "No logs found"
        
        self.log_test("Log Updates", success, details)
        return success

    def test_status_transitions(self):
        """Test that scan status properly transitions"""
        print("🔍 Testing Status Transitions...")
        
        if not self.progress_updates:
            self.log_test("Status Transitions", False, "No progress updates captured")
            return False
        
        statuses = [update.get('status') for update in self.progress_updates]
        unique_statuses = list(set(statuses))
        
        # Check for expected status progression
        has_running = 'running' in statuses
        has_completion = any(status in ['completed', 'failed'] for status in statuses)
        
        success = has_running and (has_completion or 'running' in unique_statuses)
        
        details = f"Status progression: {' -> '.join(unique_statuses)}"
        self.log_test("Status Transitions", success, details)
        
        return success

    def test_progress_accuracy(self, expected_blocks):
        """Test that progress calculations are accurate"""
        print(f"🔍 Testing Progress Accuracy (Expected {expected_blocks} blocks)...")
        
        if not self.progress_updates:
            self.log_test("Progress Accuracy", False, "No progress updates captured")
            return False
        
        final_update = self.progress_updates[-1]
        total_blocks = final_update.get('total_blocks', 0)
        blocks_scanned = final_update.get('blocks_scanned', 0)
        progress_percentage = final_update.get('progress_percentage', 0)
        
        # Check if total_blocks matches expected
        total_correct = total_blocks == expected_blocks
        
        # Check if progress percentage is calculated correctly
        expected_percentage = (blocks_scanned / total_blocks * 100) if total_blocks > 0 else 0
        percentage_correct = abs(progress_percentage - expected_percentage) < 1.0  # Allow 1% tolerance
        
        success = total_correct and percentage_correct
        
        details = (f"Total blocks: {total_blocks} (expected {expected_blocks}), "
                  f"Blocks scanned: {blocks_scanned}, "
                  f"Progress: {progress_percentage:.1f}% (calculated: {expected_percentage:.1f}%)")
        
        self.log_test("Progress Accuracy", success, details)
        
        # Additional check for the specific issue mentioned in the review request
        if expected_blocks == 1 and blocks_scanned != 1:
            print(f"   ⚠️  ISSUE DETECTED: Frontend shows {blocks_scanned} blocks scanned when it should be 1")
            print(f"   This confirms the issue reported in the review request")
        
        return success

    def test_real_time_updates(self):
        """Test that progress updates occur in real-time"""
        print("🔍 Testing Real-time Progress Updates...")
        
        if len(self.progress_updates) < 2:
            self.log_test("Real-time Updates", False, f"Only {len(self.progress_updates)} updates captured")
            return False
        
        # Check that updates have different timestamps
        timestamps = [update.get('timestamp') for update in self.progress_updates]
        unique_timestamps = len(set(timestamps))
        
        # Check that progress values change over time
        progress_values = [update.get('progress_percentage', 0) for update in self.progress_updates]
        progress_changes = len(set(progress_values)) > 1
        
        success = unique_timestamps > 1 and progress_changes
        
        details = (f"Captured {len(self.progress_updates)} updates with "
                  f"{unique_timestamps} unique timestamps, "
                  f"Progress changed: {progress_changes}")
        
        self.log_test("Real-time Updates", success, details)
        return success

    def run_single_block_test(self):
        """Run complete test for single block scan"""
        print("=" * 60)
        print("🚀 SINGLE BLOCK SCAN TEST (Block 252474)")
        print("=" * 60)
        
        # Start single block scan
        if not self.start_single_block_scan(252474):
            return False
        
        # Monitor progress
        update_count = self.monitor_progress_updates(60)
        
        # Run tests
        self.test_progress_data_structure()
        self.test_log_updates()
        self.test_status_transitions()
        self.test_progress_accuracy(1)  # Expect 1 block
        self.test_real_time_updates()
        
        return True

    def run_multi_block_test(self):
        """Run complete test for multi-block scan"""
        print("=" * 60)
        print("🚀 MULTI-BLOCK SCAN TEST (Blocks 252474-252476)")
        print("=" * 60)
        
        # Reset for new test
        self.scan_id = None
        self.progress_updates = []
        
        # Start multi-block scan
        if not self.start_multi_block_scan(252474, 252476):
            return False
        
        # Monitor progress
        update_count = self.monitor_progress_updates(90)
        
        # Run tests
        self.test_progress_data_structure()
        self.test_log_updates()
        self.test_status_transitions()
        self.test_progress_accuracy(3)  # Expect 3 blocks
        self.test_real_time_updates()
        
        return True

def main():
    print("🚀 Starting Scan Progress System Test")
    print("Focus: Progress Updates, Real-time Tracking, Log Updates, Status Transitions")
    print("=" * 80)
    
    tester = ScanProgressTester()
    
    # Test API connectivity first
    if not tester.test_health_check():
        print("❌ Cannot connect to API. Exiting.")
        return 1
    
    # Run single block test
    tester.run_single_block_test()
    
    # Wait a bit between tests
    time.sleep(5)
    
    # Run multi-block test
    tester.run_multi_block_test()
    
    # Print final results
    print("=" * 80)
    print(f"📊 FINAL RESULTS: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All scan progress tests passed!")
        return 0
    else:
        failed = tester.tests_run - tester.tests_passed
        print(f"⚠️  {failed} test(s) failed")
        
        # Specific analysis for the reported issue
        print("\n🔍 ISSUE ANALYSIS:")
        print("The review request mentioned frontend showing 50 blocks scanned when it should be 1.")
        print("Check the 'Progress Accuracy' test results above to see if this is a backend issue.")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())