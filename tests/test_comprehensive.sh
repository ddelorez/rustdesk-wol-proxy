#!/bin/bash

##############################################################################
# Comprehensive API Testing Script
# Task 1.3: Local Testing (Development)
# Tests all required test cases with curl and Apache Bench
##############################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_URL="http://localhost:5001"
API_KEY="wol_prod_test_key_1234567890_secure"
VALID_ID="123456789"
VALID_MAC="AA:BB:CC:DD:EE:FF"
RESULTS_FILE="test_results.txt"
LOG_FILE="./dev.log"

# Initialize results file
> "$RESULTS_FILE"

# Helper functions
log_test() {
    echo -e "${BLUE}>>> $1${NC}" | tee -a "$RESULTS_FILE"
}

log_pass() {
    echo -e "${GREEN}✓ PASS: $1${NC}" | tee -a "$RESULTS_FILE"
}

log_fail() {
    echo -e "${RED}✗ FAIL: $1${NC}" | tee -a "$RESULTS_FILE"
}

log_info() {
    echo -e "${YELLOW}ℹ $1${NC}" | tee -a "$RESULTS_FILE"
}

# Check if curl is available
if ! command -v curl &> /dev/null; then
    log_fail "curl is not installed"
    exit 1
fi

echo -e "${BLUE}=================================================================================${NC}"
echo -e "${BLUE}      COMPREHENSIVE API TESTING - Task 1.3${NC}"
echo -e "${BLUE}=================================================================================${NC}"
echo "" | tee -a "$RESULTS_FILE"

##############################################################################
# Test 1: Valid Request Tests
##############################################################################

log_test "Test 1: Valid Request Tests"
echo "" | tee -a "$RESULTS_FILE"

HTTP_CODE=$(curl -s -o /tmp/response.json -w "%{http_code}" \
    "$API_URL/wake?id=$VALID_ID&key=$API_KEY")

if [ "$HTTP_CODE" = "200" ]; then
    log_pass "Valid request returns HTTP 200"
    
    # Check response fields
    RESPONSE=$(cat /tmp/response.json)
    echo "Response: $RESPONSE" | tee -a "$RESULTS_FILE"
    
    if echo "$RESPONSE" | grep -q '"status":"success"'; then
        log_pass "Response contains 'status' field with 'success'"
    else
        log_fail "Response missing 'status' field or incorrect value"
    fi
    
    if echo "$RESPONSE" | grep -q "\"id\":\"$VALID_ID\""; then
        log_pass "Response contains correct 'id' field"
    else
        log_fail "Response missing 'id' field"
    fi
    
    if echo "$RESPONSE" | grep -q "\"mac\":\"$VALID_MAC\""; then
        log_pass "Response contains correct 'mac' field"
    else
        log_fail "Response missing 'mac' field"
    fi
    
    if echo "$RESPONSE" | grep -q '"timestamp".*T.*Z'; then
        log_pass "Response contains ISO 8601 UTC timestamp"
    else
        log_fail "Response missing or invalid timestamp format"
    fi
else
    log_fail "Valid request returned HTTP $HTTP_CODE (expected 200)"
fi
echo "" | tee -a "$RESULTS_FILE"

##############################################################################
# Test 2: Missing Parameter Tests
##############################################################################

log_test "Test 2: Missing Parameter Tests"
echo "" | tee -a "$RESULTS_FILE"

# Missing ID
HTTP_CODE=$(curl -s -o /tmp/response.json -w "%{http_code}" \
    "$API_URL/wake?key=$API_KEY")

if [ "$HTTP_CODE" = "400" ]; then
    log_pass "Missing ID returns HTTP 400"
    if grep -q '"code":"MISSING_PARAMETER"' /tmp/response.json; then
        log_pass "Error code is MISSING_PARAMETER"
    else
        log_fail "Error code is not MISSING_PARAMETER"
    fi
else
    log_fail "Missing ID returned HTTP $HTTP_CODE (expected 400)"
fi

# Missing key
HTTP_CODE=$(curl -s -o /tmp/response.json -w "%{http_code}" \
    "$API_URL/wake?id=$VALID_ID")

if [ "$HTTP_CODE" = "400" ]; then
    log_pass "Missing key returns HTTP 400"
    if grep -q '"code":"MISSING_PARAMETER"' /tmp/response.json; then
        log_pass "Error code is MISSING_PARAMETER"
    else
        log_fail "Error code is not MISSING_PARAMETER"
    fi
else
    log_fail "Missing key returned HTTP $HTTP_CODE (expected 400)"
fi

# Check timestamp in error response
RESPONSE=$(cat /tmp/response.json)
if echo "$RESPONSE" | grep -q '"timestamp".*T.*Z'; then
    log_pass "Error response contains ISO 8601 UTC timestamp"
else
    log_fail "Error response missing or invalid timestamp"
fi
echo "" | tee -a "$RESULTS_FILE"

##############################################################################
# Test 3: Invalid Parameter Tests
##############################################################################

log_test "Test 3: Invalid Parameter Tests"
echo "" | tee -a "$RESULTS_FILE"

# Invalid ID format (too long - 51 chars)
LONG_ID=$(printf 'a%.0s' {1..51})
HTTP_CODE=$(curl -s -o /tmp/response.json -w "%{http_code}" \
    "$API_URL/wake?id=$LONG_ID&key=$API_KEY")

if [ "$HTTP_CODE" = "400" ]; then
    log_pass "Invalid ID (too long) returns HTTP 400"
    if grep -q '"code":"INVALID_PARAMETER"' /tmp/response.json; then
        log_pass "Error code is INVALID_PARAMETER"
    else
        log_fail "Error code is not INVALID_PARAMETER"
    fi
else
    log_fail "Invalid ID returned HTTP $HTTP_CODE (expected 400)"
fi

# Invalid API key (too short - 10 chars)
HTTP_CODE=$(curl -s -o /tmp/response.json -w "%{http_code}" \
    "$API_URL/wake?id=$VALID_ID&key=short12345")

if [ "$HTTP_CODE" = "400" ]; then
    log_pass "Invalid API key (too short) returns HTTP 400"
    if grep -q '"code":"INVALID_PARAMETER"' /tmp/response.json; then
        log_pass "Error code is INVALID_PARAMETER"
    else
        log_fail "Error code is not INVALID_PARAMETER"
    fi
else
    log_fail "Invalid API key returned HTTP $HTTP_CODE (expected 400)"
fi

# Invalid ID format (non-alphanumeric)
HTTP_CODE=$(curl -s -o /tmp/response.json -w "%{http_code}" \
    "$API_URL/wake?id=123@456&key=$API_KEY")

if [ "$HTTP_CODE" = "400" ]; then
    log_pass "Invalid ID format (special chars) returns HTTP 400"
    if grep -q '"code":"INVALID_PARAMETER"' /tmp/response.json; then
        log_pass "Error code is INVALID_PARAMETER"
    else
        log_fail "Error code is not INVALID_PARAMETER"
    fi
else
    log_fail "Invalid ID (special chars) returned HTTP $HTTP_CODE (expected 400)"
fi
echo "" | tee -a "$RESULTS_FILE"

##############################################################################
# Test 4: Authentication Tests
##############################################################################

log_test "Test 4: Authentication Tests"
echo "" | tee -a "$RESULTS_FILE"

# Wrong API key
HTTP_CODE=$(curl -s -o /tmp/response.json -w "%{http_code}" \
    "$API_URL/wake?id=$VALID_ID&key=wol_prod_invalid_key_1234567890")

if [ "$HTTP_CODE" = "403" ]; then
    log_pass "Wrong API key returns HTTP 403"
    if grep -q '"code":"INVALID_KEY"' /tmp/response.json; then
        log_pass "Error code is INVALID_KEY"
    else
        log_fail "Error code is not INVALID_KEY"
    fi
else
    log_fail "Wrong API key returned HTTP $HTTP_CODE (expected 403)"
fi
echo "" | tee -a "$RESULTS_FILE"

##############################################################################
# Test 5: Not Found Tests
##############################################################################

log_test "Test 5: Not Found Tests"
echo "" | tee -a "$RESULTS_FILE"

# Unknown ID
HTTP_CODE=$(curl -s -o /tmp/response.json -w "%{http_code}" \
    "$API_URL/wake?id=999999999&key=$API_KEY")

if [ "$HTTP_CODE" = "404" ]; then
    log_pass "Unknown ID returns HTTP 404"
    if grep -q '"code":"UNKNOWN_ID"' /tmp/response.json; then
        log_pass "Error code is UNKNOWN_ID"
    else
        log_fail "Error code is not UNKNOWN_ID"
    fi
else
    log_fail "Unknown ID returned HTTP $HTTP_CODE (expected 404)"
fi
echo "" | tee -a "$RESULTS_FILE"

##############################################################################
# Test 6: Health Endpoint Tests
##############################################################################

log_test "Test 6: Health Endpoint Tests"
echo "" | tee -a "$RESULTS_FILE"

HTTP_CODE=$(curl -s -o /tmp/response.json -w "%{http_code}" \
    "$API_URL/health")

if [ "$HTTP_CODE" = "200" ]; then
    log_pass "Health endpoint returns HTTP 200"
    
    RESPONSE=$(cat /tmp/response.json)
    if echo "$RESPONSE" | grep -q '"status":"healthy"'; then
        log_pass "Health response contains correct status"
    else
        log_fail "Health response has incorrect status"
    fi
    
    if echo "$RESPONSE" | grep -q '"timestamp".*T.*Z'; then
        log_pass "Health response contains ISO 8601 UTC timestamp"
    else
        log_fail "Health response missing or invalid timestamp"
    fi
else
    log_fail "Health endpoint returned HTTP $HTTP_CODE (expected 200)"
fi
echo "" | tee -a "$RESULTS_FILE"

##############################################################################
# Test 7: Response Header Tests
##############################################################################

log_test "Test 7: Response Header Tests"
echo "" | tee -a "$RESULTS_FILE"

# Capture headers for a valid request
curl -s -D /tmp/headers.txt -o /tmp/response.json \
    "$API_URL/wake?id=$VALID_ID&key=$API_KEY" > /dev/null 2>&1

if grep -i "X-Request-ID:" /tmp/headers.txt > /dev/null; then
    REQUEST_ID=$(grep -i "X-Request-ID:" /tmp/headers.txt | cut -d' ' -f2)
    log_pass "Response contains X-Request-ID header: $REQUEST_ID"
else
    log_fail "Response missing X-Request-ID header"
fi

if grep -i "X-Request-Duration-Ms:" /tmp/headers.txt > /dev/null; then
    DURATION=$(grep -i "X-Request-Duration-Ms:" /tmp/headers.txt | cut -d' ' -f2)
    log_pass "Response contains X-Request-Duration-Ms header: ${DURATION}ms"
else
    log_fail "Response missing or invalid X-Request-Duration-Ms header"
fi
echo "" | tee -a "$RESULTS_FILE"

##############################################################################
# Test 8: Concurrent Request Tests (Apache Bench)
##############################################################################

log_test "Test 8: Concurrent Request Tests"
echo "" | tee -a "$RESULTS_FILE"

# Check if ab (Apache Bench) is available
if command -v ab &> /dev/null; then
    log_info "Running Apache Bench concurrent test (100 requests, 10 concurrent)"
    
    ab -n 100 -c 10 \
        "$API_URL/wake?id=$VALID_ID&key=$API_KEY" > /tmp/ab_results.txt 2>&1
    
    # Extract key metrics
    REQUESTS_COMPLETED=$(grep "Requests completed:" /tmp/ab_results.txt | awk '{print $NF}')
    FAILED=$(grep "Failed requests:" /tmp/ab_results.txt | awk '{print $NF}')
    
    if [ "$REQUESTS_COMPLETED" = "100" ] && [ "$FAILED" = "0" ]; then
        log_pass "All 100 concurrent requests completed successfully"
    else
        log_fail "Concurrent test issues - Completed: $REQUESTS_COMPLETED, Failed: $FAILED"
    fi
    
    # Show performance metrics
    MEAN_TIME=$(grep "Time per request:" /tmp/ab_results.txt | head -1 | awk '{print $NF}')
    REQUESTS_PER_SEC=$(grep "Requests per second:" /tmp/ab_results.txt | awk '{print $NF}')
    
    log_info "Performance - Mean time/request: $MEAN_TIME ms"
    log_info "Performance - Requests/sec: $REQUESTS_PER_SEC"
    
    echo "" >> /tmp/ab_results.txt
    cat /tmp/ab_results.txt >> "$RESULTS_FILE"
else
    log_info "Apache Bench (ab) not available, skipping concurrent load test"
fi
echo "" | tee -a "$RESULTS_FILE"

##############################################################################
# Test 9: Logging Verification Tests
##############################################################################

log_test "Test 9: Logging Verification Tests"
echo "" | tee -a "$RESULTS_FILE"

# Check if log file exists
if [ -f "$LOG_FILE" ]; then
    log_pass "Log file exists: $LOG_FILE"
    
    # Check for IP addresses in logs
    if grep -q '\[127.0.0.1\]' "$LOG_FILE" || grep -q '\[::1\]' "$LOG_FILE"; then
        log_pass "Log entries contain IP addresses"
    else
        log_info "No log entries with IP yet (or using different format)"
    fi
    
    # Check for timestamps
    if grep -q 'T.*Z' "$LOG_FILE" || grep -q '[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}' "$LOG_FILE"; then
        log_pass "Log entries contain timestamps"
    else
        log_info "Timestamps may be in different format"
    fi
    
    # Check that API key is masked
    if grep -q '***' "$LOG_FILE"; then
        log_pass "API key appears to be masked in logs"
    else
        log_info "No masked keys found (may not have sensitive logs yet)"
    fi
    
    # Show last 20 lines of log
    log_info "Last 20 lines of log file:"
    echo "------- Log File Contents -------" | tee -a "$RESULTS_FILE"
    tail -20 "$LOG_FILE" | tee -a "$RESULTS_FILE"
    echo "------- End of Log -------" | tee -a "$RESULTS_FILE"
else
    log_fail "Log file does not exist: $LOG_FILE"
fi
echo "" | tee -a "$RESULTS_FILE"

##############################################################################
# Summary
##############################################################################

echo -e "${BLUE}=================================================================================${NC}"
echo -e "${BLUE}      TEST SUMMARY${NC}"
echo -e "${BLUE}=================================================================================${NC}"
echo "" | tee -a "$RESULTS_FILE"

# Count pass/fail
PASS_COUNT=$(grep -c "^✓ PASS:" "$RESULTS_FILE" || true)
FAIL_COUNT=$(grep -c "^✗ FAIL:" "$RESULTS_FILE" || true)
INFO_COUNT=$(grep -c "^ℹ " "$RESULTS_FILE" || true)

log_info "Total Passed: $PASS_COUNT"
log_info "Total Failed: $FAIL_COUNT"
log_info "Total Informational: $INFO_COUNT"
echo "" | tee -a "$RESULTS_FILE"

# Overall result
if [ "$FAIL_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓✓✓ ALL TESTS PASSED SUCCESSFULLY ✓✓✓${NC}" | tee -a "$RESULTS_FILE"
    exit 0
else
    echo -e "${RED}✗✗✗ SOME TESTS FAILED ✗✗✗${NC}" | tee -a "$RESULTS_FILE"
    exit 1
fi
