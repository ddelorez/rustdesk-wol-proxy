# RustDesk WOL Proxy - Developer Guide

## Overview

This guide provides comprehensive documentation for developers working on the RustDesk WOL Proxy codebase. It covers code structure, architecture, development setup, testing procedures, and contribution guidelines.

**Version**: 1.0.0  
**Last Updated**: 2026-02-10  
**Language**: Python 3.x  
**Framework**: Flask

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Development Setup](#development-setup)
3. [Code Architecture](#code-architecture)
4. [Module Documentation](#module-documentation)
5. [Configuration Management](#configuration-management)
6. [Testing](#testing)
7. [Logging & Debugging](#logging--debugging)
8. [Deployment](#deployment)
9. [Contributing](#contributing)

---

## Project Structure

```
rustdesk-wol-proxy/
├── app.py                      # Main Flask application (Google-style docstrings)
├── requirements.txt            # Python dependencies
├── .env.example               # Environment configuration template
├── .gitignore                 # Git ignore rules
├── README.md                  # User documentation
├── ARCHITECTURE.md            # System architecture & deployment
├── API_DOCUMENTATION.md       # API endpoint reference
├── DEVELOPER_GUIDE.md        # This file
├── rustdesk-wol.service      # Systemd service file
├── test_comprehensive.sh     # Bash integration tests
├── test_comprehensive.py     # Python integration tests
├── run_all_tests.py         # Test orchestration script
├── TEST_REPORT.md           # Most recent test results
├── TESTING_SUMMARY.md       # Testing documentation
└── planning.md              # Development planning notes
```

### Key Files

| File | Purpose | Types |
|------|---------|-------|
| `app.py` | Main application code | Flask, REST API |
| `requirements.txt` | Python package dependencies | Dependencies |
| `.env.example` | Configuration template | Configuration |
| `rustdesk-wol.service` | Linux systemd service | Deployment |
| `test_*.py` | Python unit/integration tests | Testing |
| `test_comprehensive.sh` | Bash shell integration tests | Testing |

---

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git
- Linux/Unix environment (or WSL on Windows)

### Installation

1. **Clone Repository**:
```bash
git clone https://github.com/ddelore/rustdesk-wol-proxy.git
cd rustdesk-wol-proxy
```

2. **Create Virtual Environment**:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Install Dependencies**:
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

4. **Configure Environment**:
```bash
cp .env.example .env
# Edit .env and set:
# - WOL_API_KEY=wol_dev_your_test_key_1234567890
# - BROADCAST_IP=127.0.0.1 (for testing)
# - LOG_FILE=./wol.log
```

5. **Run Development Server**:
```bash
python app.py
```

The server will start on `http://localhost:5001`

### Development Dependencies

Create a `requirements-dev.txt` if adding development-only packages:
```
pytest>=7.0.0
pytest-cov>=4.0.0
black>=22.0.0
pylint>=2.15.0
```

---

## Code Architecture

### Application Flow

```
Request arrives
    ↓
↓─→ before_request_handler()         [Request middleware]
    ├─ Generate request_id
    └─ Start timer
    ↓
↓─→ Route handler (/wake or /health)
    ├─ Validate parameters
    ├─ Authenticate (API key)
    ├─ Authorize (device ID)
    ├─ Execute action (send WOL)
    └─ Return response
    ↓
↓─→ after_request()                  [Response middleware]
    ├─ Add X-Request-ID header
    ├─ Add X-Request-Duration-Ms
    └─ Return response
    ↓
Response sent to client
```

### Code Sections

#### 1. Configuration Management (1.1.1)

Located at lines 18-93 in `app.py`

**Purpose**: Load and validate environment configuration at startup

**Functions**:
- `load_configuration()`: Validates all required environment variables
  - Loads from `.env` file (development)
  - Validates API key strength (20-256 chars)
  - Validates broadcast IP format
  - Creates log directory if needed
  - Returns configuration dictionary

**Key Variables**:
- `CONFIG`: Dictionary with all application settings
- `API_KEY`: Validated authentication key
- `BROADCAST_IP`: Network broadcast address
- `LOG_FILE`: Log file path
- `ALLOWED_IDS`: Device ID to MAC mappings

#### 2. Logging Enhancements (1.1.3)

Located at lines 98-137 in `app.py`

**Purpose**: Configure comprehensive logging with request context

**Classes**:
- `ContextualFilter`: Logging filter that adds request context
  - Injects remote client IP address
  - Injects request ID for tracing
  - Enables log analysis per-client

**Configuration**:
- Handler: `RotatingFileHandler` (5MB per file, 3 backups)
- Format: `%(asctime)s - %(levelname)s - [%(remote_addr)s] - %(message)s`
- Level: `INFO`

**Log Output Example**:
```
2026-02-10 20:12:52,493 - INFO - [192.168.1.100] - WOL packet sent to AA:BB:CC:DD:EE:FF (ID: 123456789, key: wol_prod_se***)
```

#### 3. Input Validation (1.1.4)

Located at lines 152-284 in `app.py`

**Purpose**: Validate user-supplied parameters before processing

**Functions**:
- `validate_id_format(rustdesk_id)`: Validates RustDesk device ID
  - Required (not empty)
  - Max 50 characters
  - Alphanumeric only
  - Returns (is_valid, error_message)

- `validate_api_key_format(api_key)`: Validates API key format
  - Required (not empty)
  - Min 20 characters
  - Max 256 characters
  - Returns (is_valid, error_message)

**Security Considerations**:
- Prevents injection attacks through strict validation
- Limits parameter sizes to prevent DoS
- Alphanumeric-only ID prevents special character exploitation

#### 4. Response Enhancements (1.1.5)

Located throughout `app.py`

**Purpose**: Standardized JSON responses with timestamps and tracing

**Components**:
- `get_iso_timestamp()`: Generates ISO 8601 UTC timestamps
- `generate_request_id()`: Creates UUID4 request identifiers
- Response headers: `X-Request-ID`, `X-Request-Duration-Ms`
- Consistent JSON structure for all endpoints

**Response Examples**:
```json
{
  "status": "success|error",
  "code": "ERROR_CODE",
  "message": "Human-readable description",
  "timestamp": "2026-02-10T20:12:52.493Z"
}
```

#### 5. Error Handling (1.1.2)

Located at lines 357-537 in `app.py`

**Purpose**: Comprehensive error handling for all failure scenarios

**Error Types**:
- **Parameter Errors**: Missing or invalid input (400)
- **Authentication Errors**: Invalid API key (403)
- **Authorization Errors**: Unknown device ID (404)
- **Permission Errors**: Insufficient privileges (500)
- **Network Errors**: Network unreachable (500)
- **Generic Errors**: Unexpected exceptions (500)

**Error Categories**:
```python
# OSError handling (permission, network issues)
OSError with errno 1   → PERMISSION_DENIED
OSError with errno 101 → NETWORK_ERROR
Other OSError          → SEND_FAILED

# General exceptions
Generic Exception      → SEND_FAILED
```

### Middleware Flow

#### Before Request

```python
@app.before_request
def before_request_handler():
    """Set up request context for tracing."""
    g.request_id = generate_request_id()  # UUID4
    g.start_time = time.time()             # Unix timestamp
```

**When**: Runs before every request  
**Purpose**: Initialize per-request context  
**Data**: Stored in Flask's g object

#### After Request

```python
@app.after_request
def after_request(response):
    """Add tracing headers to response."""
    response.headers["X-Request-ID"] = g.request_id
    response.headers["X-Request-Duration-Ms"] = duration_ms
    return response
```

**When**: Runs after response is generated  
**Purpose**: Add tracing information to response  
**Output**: HTTP headers

---

## Module Documentation

### Class: ContextualFilter

**Location**: Line 100  
**Base Class**: `logging.Filter`

**Purpose**: Add request context to all log records

**Methods**:
- `filter(record: LogRecord) → bool`: Enhance log record with context
  - Adds `remote_addr`: Client IP address
  - Adds `request_id`: Request UUID
  - Returns True (always log the record)

**Usage**:
```python
contextual_filter = ContextualFilter()
handler.addFilter(contextual_filter)
```

### Function: validate_id_format()

**Location**: Line 152  
**Signature**: `validate_id_format(rustdesk_id: str) → Tuple[bool, Optional[str]]`

**Parameters**:
- `rustdesk_id` (str): Device identifier to validate

**Returns**:
- Tuple of (is_valid, error_message)
- If valid: (True, None)
- If invalid: (False, "error description")

**Validation Rules**:
```python
1. Non-empty (required)
2. Max 50 characters
3. Alphanumeric only: [a-zA-Z0-9]+
```

**Examples**:
```python
validate_id_format("123456789")                    # (True, None)
validate_id_format("")                             # (False, "required")
validate_id_format("a" * 51)                       # (False, "exceeds maximum")
validate_id_format("id-with-dashes")               # (False, "must be alphanumeric")
```

### Function: validate_api_key_format()

**Location**: Line 171  
**Signature**: `validate_api_key_format(api_key: str) → Tuple[bool, Optional[str]]`

**Parameters**:
- `api_key` (str): API key to validate

**Returns**:
- Tuple of (is_valid, error_message)
- If valid: (True, None)
- If invalid: (False, "error description")

**Validation Rules**:
```python
1. Non-empty (required)
2. Min 20 characters
3. Max 256 characters
```

**Examples**:
```python
validate_api_key_format("wol_prod_key1234567890")  # (True, None)
validate_api_key_format("short")                   # (False, "too short")
validate_api_key_format("a" * 257)                 # (False, "exceeds maximum")
```

### Function: get_iso_timestamp()

**Location**: Line 190  
**Signature**: `get_iso_timestamp() → str`

**Returns**: ISO 8601 formatted timestamp string

**Format**: `YYYY-MM-DDTHH:MM:SS.sssZ`

**Examples**:
```python
get_iso_timestamp()  # "2026-02-10T20:12:52.493Z"
```

**Notes**:
- Uses UTC timezone
- Millisecond precision
- Z suffix indicates UTC (Zulu time)

### Function: generate_request_id()

**Location**: Line 197  
**Signature**: `generate_request_id() → str`

**Returns**: UUID4 string identifier

**Example**:
```python
generate_request_id()  # "f47ac10b-58cc-4372-a567-0e02b2c3d479"
```

**Format**: Standard UUID4 (36 characters with hyphens)

### Route: POST /wake

**Location**: Line 240  
**Method**: GET (query parameters)  
**Authentication**: Required (API key)

**Parameters**:
- `id` (query): RustDesk device ID
- `key` (query): API authentication key

**Returns**: JSON response with WOL result

**Status Codes**:
- 200: Success
- 400: Invalid parameters
- 403: Invalid key
- 404: Unknown ID
- 500: System error

**Implementation Notes**:
1. Extract query parameters
2. Validate ID format
3. Validate API key format
4. Check API key matches
5. Lookup MAC address
6. Send magic packet via wakeonlan library
7. Log and return response

### Route: GET /health

**Location**: Line 439  
**Method**: GET  
**Authentication**: Not required

**Returns**: Simple JSON status

**Status Code**: Always 200

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "ISO8601"
}
```

---

## Configuration Management

### Environment Variables

All configuration comes from environment variables, loaded via `load_dotenv()`:

#### WOL_API_KEY (REQUIRED)

```bash
export WOL_API_KEY="wol_prod_securekey1234567890"
```

**Validation**:
- Minimum 20 characters
- Maximum 256 characters
- Checked at startup; app won't start without valid key

**Usage**:
```python
api_key = os.getenv("WOL_API_KEY")
if len(api_key) < 20:
    raise ValueError("API key too short")
```

#### BROADCAST_IP (OPTIONAL)

```bash
export BROADCAST_IP="10.10.10.255"
```

**Default**: `10.10.10.255`  
**Validation**: Valid IPv4 address format  
**Usage**: UDP broadcast address for WOL packets

#### LOG_FILE (OPTIONAL)

```bash
export LOG_FILE="/var/log/rustdesk-wol-proxy.log"
```

**Default**: `/var/log/rustdesk-wol-proxy.log`  
**Validation**: Directory must exist or be creatable  
**Usage**: Path to application log file

### Device Configuration

Device mappings are configured in code in `ALLOWED_IDS` dictionary:

```python
ALLOWED_IDS = {
    "123456789": "AA:BB:CC:DD:EE:FF",
    "987654321": "11:22:33:44:55:66",
}
```

**To add devices**:
1. Edit `app.py`
2. Add entry: `"device_id": "MAC:ADDRESS"`
3. Restart service

**MAC Address Format**:
- Colon-separated hexadecimal
- Example: `AA:BB:CC:DD:EE:FF`
- Must be valid for each device

---

## Testing

### Test Files

| File | Type | Purpose |
|------|------|---------|
| `test_comprehensive.py` | Python | Unit and integration tests |
| `test_comprehensive.sh` | Bash | Shell-based integration tests |
| `run_all_tests.py` | Python | Test orchestration |

### Running Tests

#### Run All Tests

```bash
python run_all_tests.py
```

**Output**: Summary of all test results

#### Run Python Tests

```bash
python -m pytest test_comprehensive.py -v
```

**Options**:
- `-v`: Verbose output
- `-s`: Show print statements
- `-k "pattern"`: Run specific tests
- `--tb=short`: Short traceback format

#### Run Bash Tests

```bash
bash test_comprehensive.sh
```

**Output**: Curl command results with response validation

### Test Coverage

**Current Coverage**: 33 passing tests covering:

1. **Configuration Tests**:
   - Valid/invalid API keys
   - Valid/invalid broadcast IPs
   - Configuration at startup

2. **Authentication Tests**:
   - Valid API key
   - Invalid API key
   - Missing API key

3. **Parameter Validation Tests**:
   - Valid/invalid device IDs
   - Valid/invalid API key formats
   - Missing parameters

4. **WOL Functionality Tests**:
   - Successful packet send
   - Device not found
   - Permission errors
   - Network errors

5. **Health Check Tests**:
   - Health endpoint response
   - Timestamp format
   - Version information

6. **Response Format Tests**:
   - JSON structure
   - ISO 8601 timestamps
   - Request ID headers
   - Duration calculations

7. **Error Handling Tests**:
   - 400 Bad Request
   - 403 Forbidden
   - 404 Not Found
   - 500 Server Error
   - 405 Method Not Allowed

### Writing New Tests

#### Test Structure

```python
def test_endpoint_scenario():
    """Test description (docstring).
    
    Should test specific behavior or edge case.
    Verify expected output or error handling.
    """
    # Setup
    test_data = {
        "param": "value"
    }
    
    # Execute
    response = client.get("/wake", query_string=test_data)
    
    # Verify
    assert response.status_code == 200
    assert response.json["status"] == "success"
```

#### Test Naming Conventions

- `test_[feature]_[scenario]`: e.g., `test_wake_valid_request`
- `test_[error_type]`: e.g., `test_invalid_api_key`
- `test_health_check`: For health endpoint tests

#### Assertions

```python
# Status code
assert response.status_code == 200

# JSON response
assert response.json["status"] == "success"
assert "timestamp" in response.json

# Headers
assert "X-Request-ID" in response.headers
assert "X-Request-Duration-Ms" in response.headers

# Error responses
assert response.json["code"] == "ERROR_CODE"
```

---

## Logging & Debugging

### Log File Location

```
/var/log/rustdesk-wol-proxy.log
```

### Log Format

```
2026-02-10 20:12:52,493 - INFO - [192.168.1.100] - WOL packet sent to AA:BB:CC:DD:EE:FF (ID: 123456789, key: wol_prod_se***)
```

**Components**:
- Timestamp: `2026-02-10 20:12:52,493`
- Level: `INFO`, `WARNING`, `ERROR`
- Remote Address: `[192.168.1.100]`
- Message: Description of event

### Log Levels

| Level | Severity | Use Case |
|-------|----------|----------|
| INFO | Normal | Successful operations, startup |
| WARNING | Minor | Invalid authentication, parameter errors |
| ERROR | Major | System failures, network errors |

### Viewing Logs

```bash
# Real-time logs
tail -f /var/log/rustdesk-wol-proxy.log

# Last 100 lines
tail -n 100 /var/log/rustdesk-wol-proxy.log

# Search for errors
grep ERROR /var/log/rustdesk-wol-proxy.log

# Search by IP address
grep "192.168.1.100" /var/log/rustdesk-wol-proxy.log

# Search by request ID
grep "f47ac10b-58cc-4372-a567-0e02b2c3d479" /var/log/rustdesk-wol-proxy.log
```

### Debugging

#### Enable Debug Logging

Modify `app.py` line 132:
```python
app.logger.setLevel(logging.DEBUG)  # Instead of logging.INFO
```

**WARNING**: Debug mode is verbose; only for development/troubleshooting.

#### Use Flask's Built-in Debugger

For development, modify `app.py` line 729:
```python
app.run(host='0.0.0.0', port=5001, debug=True)
```

**WARNING**: Never enable debug mode in production!

#### Request Tracing

Every response includes `X-Request-ID`:

```bash
curl -i http://localhost:5001/health
X-Request-ID: f47ac10b-58cc-4372-a567-0e02b2c3d479

# Find all logs for this request
grep "f47ac10b-58cc-4372-a567-0e02b2c3d479" /var/log/rustdesk-wol-proxy.log
```

#### Print Debugging

Add print statements to code (Flask will show in console):
```python
print(f"DEBUG: rustdesk_id = {rustdesk_id}")
print(f"DEBUG: response = {response}")
```

---

## Deployment

### Development Deployment

```bash
python app.py
```

Runs server on `http://localhost:5001`

### Production Deployment

See `ARCHITECTURE.md` for complete deployment procedures.

**Quick Summary**:

1. Create directory: `/opt/rustdesk-wol-proxy`
2. Clone repository
3. Create virtual environment
4. Install dependencies
5. Configure `.env` file
6. Create log directory: `/var/log/rustdesk-wol`
7. Create system user: `rustdesk-wol`
8. Install systemd service: `/etc/systemd/system/rustdesk-wol.service`
9. Enable and start service: `systemctl enable --now rustdesk-wol`

### Verification Commands

```bash
# Service running?
systemctl is-active rustdesk-wol

# Service enabled?
systemctl is-enabled rustdesk-wol

# Port listening?
ss -tlnp | grep 5001

# Health check?
curl http://localhost:5001/health

# Log file exists?
ls -lh /var/log/rustdesk-wol-proxy.log
```

---

## Contributing

### Code Style

- Follow PEP 8 guidelines
- Use 4-space indentation
- Use Google-style docstrings
- Add type hints where practical
- Keep functions focused and small

### Docstring Template

```python
def function_name(param1: str, param2: int) -> bool:
    """Brief description of function.
    
    Longer detailed description of what the function does,
    including any important behavior or side effects.
    
    Args:
        param1 (str): Description of param1.
        param2 (int): Description of param2.
    
    Returns:
        bool: Description of return value.
    
    Examples:
        >>> function_name("test", 42)
        True
    
    Raises:
        ValueError: If param1 is empty.
    
    Note:
        Any additional notes about the function.
    """
```

### Making Changes

1. Create feature branch: `git checkout -b feature/description`
2. Make changes with clean commits
3. Run tests: `python run_all_tests.py`
4. Update documentation
5. Commit with clear messages
6. Push and create pull request

### Commit Messages

```
feat: Add new WOL retry logic

- Implement exponential backoff
- Add retry configuration
- Update tests

Fixes #123
```

**Format**:
- Type: feat, fix, docs, test, refactor
- Summary: Present tense, 50 chars max
- Detail: Bullet points for multiple changes
- Reference: Issue number if applicable

### Pull Request Checklist

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] Docstrings added/updated
- [ ] Commit messages are clear
- [ ] No debug code left in

---

## Troubleshooting

### Import Errors

```
ModuleNotFoundError: No module named 'flask'
```

**Solution**: Install dependencies in virtual environment
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Port Already in Use

```
OSError: [Errno 48] Address already in use
```

**Solution**: Kill process on port 5001
```bash
lsof -i :5001          # Find process ID
kill -9 <PID>          # Kill process
# Or use different port in app.run()
```

### Permission Denied (WOL)

```
OSError: [Errno 1] Operation not permitted
```

**Solution**: Run with elevated privileges
```bash
sudo python app.py

# Or for production:
systemctl status rustdesk-wol  # Check service status
sudo systemctl restart rustdesk-wol
```

### Log File Write Errors

```
PermissionError: [Errno 13] Permission denied: '/var/log/rustdesk-wol-proxy.log'
```

**Solution**: Fix log directory/file permissions
```bash
sudo mkdir -p /var/log/rustdesk-wol
sudo touch /var/log/rustdesk-wol-proxy.log
sudo chown rustdesk-wol:rustdesk-wol /var/log/rustdesk-wol-proxy.log
```

---

## Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Python PEP 8](https://www.python.org/dev/peps/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [RFC 3986 - URI Specification](https://tools.ietf.org/html/rfc3986)
- [ISO 8601 - Date/Time Format](https://www.iso.org/iso-8601-date-and-time-format.html)

---

**Document Version**: 1.0.0  
**Last Updated**: 2026-02-10  
**Maintainer**: Development Team
