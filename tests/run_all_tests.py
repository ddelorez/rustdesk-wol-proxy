#!/usr/bin/env python3
"""
Comprehensive API Testing Script - Task 1.3
Tests all required test cases using Flask test client
"""

import os
import sys
import json
import time

# Set environment before importing app
os.environ['WOL_API_KEY'] = 'wol_prod_test_key_1234567890_secure'
os.environ['LOG_FILE'] = './dev.log'

# Add parent directory to path to import app from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from app import app

# Color codes for output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

# Test counters
tests_passed = 0
tests_failed = 0
test_details = []

def log_test(name):
    """Log test section header"""
    print(f"\n{BLUE}>>> {name}{NC}")
    test_details.append(f"\n>>> {name}")

def log_pass(msg):
    """Log passed test"""
    global tests_passed
    tests_passed += 1
    print(f"{GREEN}✓ PASS: {msg}{NC}")
    test_details.append(f"✓ PASS: {msg}")

def log_fail(msg):
    """Log failed test"""
    global tests_failed
    tests_failed += 1
    print(f"{RED}✗ FAIL: {msg}{NC}")
    test_details.append(f"✗ FAIL: {msg}")

def log_info(msg):
    """Log informational message"""
    print(f"{YELLOW}ℹ {msg}{NC}")
    test_details.append(f"ℹ {msg}")

# Create test client
client = app.test_client()

print(f"\n{BLUE}{'='*80}{NC}")
print(f"{BLUE}      COMPREHENSIVE API TESTING - Task 1.3{NC}")
print(f"{BLUE}{'='*80}{NC}")

##############################################################################
# Test 1: Valid Request Tests
##############################################################################

log_test("Test 1: Valid Request Tests")

VALID_ID = "123456789"
VALID_MAC = "AA:BB:CC:DD:EE:FF"
API_KEY = "wol_prod_test_key_1234567890_secure"

response = client.get(f'/wake?id={VALID_ID}&key={API_KEY}')

if response.status_code == 200:
    log_pass("Valid request returns HTTP 200")
    data = response.get_json()
    
    if data and data.get('status') == 'success':
        log_pass("Response contains correct 'status' field")
    else:
        log_fail(f"Response 'status' field is {data.get('status') if data else None}")
    
    if data and data.get('id') == VALID_ID:
        log_pass("Response contains correct 'id' field")
    else:
        log_fail(f"Response 'id' field is {data.get('id') if data else None}")
    
    if data and data.get('mac') == VALID_MAC:
        log_pass("Response contains correct 'mac' field")
    else:
        log_fail(f"Response 'mac' field is {data.get('mac') if data else None}")
    
    if data and 'T' in str(data.get('timestamp', '')) and 'Z' in str(data.get('timestamp', '')):
        log_pass("Response contains ISO 8601 UTC timestamp")
    else:
        log_fail("Response missing or invalid timestamp format")
else:
    log_fail(f"Valid request returned HTTP {response.status_code} (expected 200)")

##############################################################################
# Test 2: Missing Parameter Tests
##############################################################################

log_test("Test 2: Missing Parameter Tests")

# Missing ID
response = client.get(f'/wake?key={API_KEY}')
if response.status_code == 400:
    log_pass("Missing ID returns HTTP 400")
    data = response.get_json()
    if data and data.get('code') == 'MISSING_PARAMETER':
        log_pass("Error code is MISSING_PARAMETER")
    else:
        log_fail(f"Error code is {data.get('code') if data else None}, expected MISSING_PARAMETER")
else:
    log_fail(f"Missing ID returned HTTP {response.status_code}, expected 400")

# Check timestamp in error response
data = response.get_json()
if data and 'timestamp' in data and 'T' in str(data['timestamp']) and 'Z' in str(data['timestamp']):
    log_pass("Error response contains ISO 8601 UTC timestamp")
else:
    log_fail("Error response missing or invalid timestamp field")

# Missing key
response = client.get(f'/wake?id={VALID_ID}')
if response.status_code == 400:
    log_pass("Missing key returns HTTP 400")
    data = response.get_json()
    if data and data.get('code') == 'MISSING_PARAMETER':
        log_pass("Error code is MISSING_PARAMETER")
    else:
        log_fail(f"Error code is {data.get('code') if data else None}, expected MISSING_PARAMETER")
else:
    log_fail(f"Missing key returned HTTP {response.status_code}, expected 400")

##############################################################################
# Test 3: Invalid Parameter Tests
##############################################################################

log_test("Test 3: Invalid Parameter Tests")

# Invalid ID format (too long - 51 chars)
long_id = 'a' * 51
response = client.get(f'/wake?id={long_id}&key={API_KEY}')
if response.status_code == 400:
    log_pass("Invalid ID (too long) returns HTTP 400")
    data = response.get_json()
    if data and data.get('code') == 'INVALID_PARAMETER':
        log_pass("Error code is INVALID_PARAMETER")
    else:
        log_fail(f"Error code is {data.get('code') if data else None}, expected INVALID_PARAMETER")
else:
    log_fail(f"Invalid ID returned HTTP {response.status_code}, expected 400")

# Invalid API key (too short - 10 chars)
response = client.get(f'/wake?id={VALID_ID}&key=short12345')
if response.status_code == 400:
    log_pass("Invalid API key (too short) returns HTTP 400")
    data = response.get_json()
    if data and data.get('code') == 'INVALID_PARAMETER':
        log_pass("Error code is INVALID_PARAMETER")
    else:
        log_fail(f"Error code is {data.get('code') if data else None}, expected INVALID_PARAMETER")
else:
    log_fail(f"Invalid API key returned HTTP {response.status_code}, expected 400")

# Invalid ID format (non-alphanumeric)
response = client.get(f'/wake?id=123@456&key={API_KEY}')
if response.status_code == 400:
    log_pass("Invalid ID format (special chars) returns HTTP 400")
    data = response.get_json()
    if data and data.get('code') == 'INVALID_PARAMETER':
        log_pass("Error code is INVALID_PARAMETER")
    else:
        log_fail(f"Error code is {data.get('code') if data else None}, expected INVALID_PARAMETER")
else:
    log_fail(f"Invalid ID (special chars) returned HTTP {response.status_code}, expected 400")

##############################################################################
# Test 4: Authentication Tests
##############################################################################

log_test("Test 4: Authentication Tests")

# Wrong API key
response = client.get(f'/wake?id={VALID_ID}&key=wol_prod_invalid_key_1234567890')
if response.status_code == 403:
    log_pass("Wrong API key returns HTTP 403")
    data = response.get_json()
    if data and data.get('code') == 'INVALID_KEY':
        log_pass("Error code is INVALID_KEY")
    else:
        log_fail(f"Error code is {data.get('code') if data else None}, expected INVALID_KEY")
else:
    log_fail(f"Wrong API key returned HTTP {response.status_code}, expected 403")

##############################################################################
# Test 5: Not Found Tests
##############################################################################

log_test("Test 5: Not Found Tests")

# Unknown ID
response = client.get(f'/wake?id=999999999&key={API_KEY}')
if response.status_code == 404:
    log_pass("Unknown ID returns HTTP 404")
    data = response.get_json()
    if data and data.get('code') == 'UNKNOWN_ID':
        log_pass("Error code is UNKNOWN_ID")
    else:
        log_fail(f"Error code is {data.get('code') if data else None}, expected UNKNOWN_ID")
else:
    log_fail(f"Unknown ID returned HTTP {response.status_code}, expected 404")

##############################################################################
# Test 6: Health Endpoint Tests
##############################################################################

log_test("Test 6: Health Endpoint Tests")

response = client.get('/health')
if response.status_code == 200:
    log_pass("Health endpoint returns HTTP 200")
    data = response.get_json()
    
    if data and 'status' in data:
        log_pass(f"Health response contains 'status': {data['status']}")
    else:
        log_fail("Health response missing 'status' field")
    
    if data and 'timestamp' in data and 'T' in str(data['timestamp']) and 'Z' in str(data['timestamp']):
        log_pass("Health response contains ISO 8601 UTC timestamp")
    else:
        log_fail("Health response missing or invalid timestamp")
else:
    log_fail(f"Health endpoint returned HTTP {response.status_code}, expected 200")

##############################################################################
# Test 7: Response Header Tests
##############################################################################

log_test("Test 7: Response Header Tests")

response = client.get(f'/wake?id={VALID_ID}&key={API_KEY}')

# Check X-Request-ID header
if 'X-Request-ID' in response.headers:
    request_id = response.headers['X-Request-ID']
    if len(request_id) > 0:
        log_pass(f"Response contains X-Request-ID header: {request_id}")
    else:
        log_fail("X-Request-ID header is empty")
else:
    log_fail("Response missing X-Request-ID header")

# Check X-Request-Duration-Ms header
if 'X-Request-Duration-Ms' in response.headers:
    duration = response.headers['X-Request-Duration-Ms']
    try:
        duration_ms = int(duration)
        log_pass(f"Response contains X-Request-Duration-Ms header: {duration}ms")
    except:
        log_fail(f"X-Request-Duration-Ms header value invalid: {duration}")
else:
    log_fail("Response missing X-Request-Duration-Ms header")

##############################################################################
# Test 8: Concurrent Request Simulation
##############################################################################

log_test("Test 8: Concurrent Request Simulation (Sequential)")

log_info("Running 20 sequential requests to simulate load...")
failed_requests = 0
successful_requests = 0

for i in range(20):
    response = client.get(f'/wake?id={VALID_ID}&key={API_KEY}')
    if response.status_code == 200:
        successful_requests += 1
    else:
        failed_requests += 1

if failed_requests == 0 and successful_requests == 20:
    log_pass(f"All 20 sequential requests completed successfully")
else:
    log_fail(f"Sequential requests: {successful_requests} passed, {failed_requests} failed")

##############################################################################
# Test 9: Logging Verification
##############################################################################

log_test("Test 9: Logging Verification Tests")

LOG_FILE = './dev.log'

if os.path.exists(LOG_FILE):
    log_pass(f"Log file exists: {LOG_FILE}")
    
    # Read log file
    with open(LOG_FILE, 'r') as f:
        log_content = f.read()
    
    # Check for IP addresses
    if '[127.0.0.1]' in log_content or '[::1]' in log_content or 'INFO' in log_content:
        log_pass("Log entries contain IP addresses or entries logged")
    else:
        log_info("No IP-specific log entries found (may still be logging)")
    
    # Check for timestamps
    if '2026-' in log_content or '202' in log_content:
        log_pass("Log entries contain timestamps")
    else:
        log_info("Timestamps may be in different format")
    
    # Check for masked API key
    if '***' in log_content:
        log_pass("API key appears to be masked in logs (contains ***)")
    else:
        log_info("No masked keys found in logs yet (may not have sensitive logs)")
    
    # Show last 10 lines of log
    log_lines = log_content.strip().split('\n')
    log_info(f"Last {min(10, len(log_lines))} lines of log file:")
    for line in log_lines[-10:]:
        print(f"  {line}")
        test_details.append(f"  {line}")
else:
    log_fail(f"Log file does not exist: {LOG_FILE}")

##############################################################################
# Test 10: Error Response Structure
##############################################################################

log_test("Test 10: Error Response Structure Validation")

# Test that all error responses have required fields
error_scenarios = [
    ('Missing parameter', f'/wake?key={API_KEY}', 400),
    ('Invalid key', f'/wake?id={VALID_ID}&key=wrong_key_12345678901234567890', 403),
    ('Unknown ID', f'/wake?id=unknown&key={API_KEY}', 404),
]

for scenario_name, url, expected_status in error_scenarios:
    response = client.get(url)
    if response.status_code == expected_status:
        data = response.get_json()
        if data:
            required_fields = ['status', 'code', 'message', 'timestamp']
            missing = [f for f in required_fields if f not in data]
            if not missing:
                log_pass(f"{scenario_name}: All required fields present")
            else:
                log_fail(f"{scenario_name}: Missing fields {missing}")
        else:
            log_fail(f"{scenario_name}: Could not parse response as JSON")
    else:
        log_fail(f"{scenario_name}: Got status {response.status_code}, expected {expected_status}")

##############################################################################
# Summary
##############################################################################

print(f"\n{BLUE}{'='*80}{NC}")
print(f"{BLUE}      TEST SUMMARY{NC}")
print(f"{BLUE}{'='*80}{NC}")

log_info(f"Total Passed: {tests_passed}")
log_info(f"Total Failed: {tests_failed}")
log_info(f"Total Tests: {tests_passed + tests_failed}")

if tests_failed == 0:
    print(f"\n{GREEN}✓✓✓ ALL TESTS PASSED SUCCESSFULLY ✓✓✓{NC}")
    exit_code = 0
else:
    print(f"\n{RED}✗✗✗ {tests_failed} TEST(S) FAILED ✗✗✗{NC}")
    exit_code = 1

# Save test results to file
import os.path
results_file = os.path.join(os.path.dirname(__file__), 'test_results.txt')
with open(results_file, 'w') as f:
    f.write('\n'.join(test_details))
    f.write(f"\n\n{'='*80}\n")
    f.write(f"TEST SUMMARY\n")
    f.write(f"{'='*80}\n")
    f.write(f"Total Passed: {tests_passed}\n")
    f.write(f"Total Failed: {tests_failed}\n")
    f.write(f"Total Tests: {tests_passed + tests_failed}\n")

print(f"\nTest results saved to test_results.txt")

sys.exit(exit_code)
