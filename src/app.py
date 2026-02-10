"""RustDesk WOL Proxy API server.

This module implements a Flask-based REST API for sending Wake-on-LAN (WOL)
commands to computers on a network. It provides secure API authentication,
comprehensive error handling, detailed logging, and health check monitoring.

Key Features:
    - WOL packet transmission to registered device MAC addresses
    - API key authentication with format validation
    - Request ID tracking for distributed tracing
    - Rotating file logging with contextual information
    - Comprehensive error handling with specific error codes
    - Health check endpoint for monitoring

Configuration:
    The application is configured via environment variables:
    - WOL_API_KEY: Authentication key (min 20 chars, max 256 chars) [REQUIRED]
    - BROADCAST_IP: Network broadcast address (default: 10.10.10.255)
    - LOG_FILE: Log file path (default: /var/log/rustdesk-wol-proxy.log)
    - ID_TO_MAC_MAPPING: Device ID to MAC address mappings [REQUIRED]

Example:
    Set environment variables before running:
    $ export WOL_API_KEY="wol_prod_<strong_random_key>"
    $ export BROADCAST_IP="10.10.10.255"
    $ export LOG_FILE="/var/log/rustdesk-wol-proxy.log"
    $ python app.py

    The server will start on http://0.0.0.0:5001

Typical Usage:
    Send WOL packet to a registered device:
    $ curl "http://localhost:5001/wake?id=123456789&key=wol_prod_KEY"

    Check server health:
    $ curl http://localhost:5001/health
"""

from flask import Flask, request, jsonify, g
import logging
from logging.handlers import RotatingFileHandler
import wakeonlan
import os
import re
import uuid
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

# ==============================
# 1.1.1 - CONFIGURATION MANAGEMENT
# ==============================

# Load environment from .env file (if present) for development
# In production, .env will be loaded by systemd EnvironmentFile directive
load_dotenv()


def load_configuration():
    """Load and validate all configuration at startup.
    
    Loads configuration from environment variables with comprehensive validation.
    Ensures all required settings are present and have valid formats. Raises
    ValueError if any configuration requirement is not met.
    
    Returns:
        dict: Configuration dictionary with keys:
            - 'API_KEY': Validated authentication key (string, 20-256 chars)
            - 'BROADCAST_IP': Validated IPv4 broadcast address (string)
            - 'LOG_FILE': Validated log file path (string)
            - 'ALLOWED_IDS': Device ID to MAC address mappings (dict)
    
    Raises:
        ValueError: If any required configuration is missing, invalid, or
                   if log directory cannot be created.
    
    Examples:
        >>> config = load_configuration()
        >>> config['API_KEY']
        'wol_prod_example_key_1234567890'
        >>> config['ALLOWED_IDS']['123456789']
        'AA:BB:CC:DD:EE:FF'
    
    Note:
        - WOL_API_KEY must be at least 20 characters for security
        - BROADCAST_IP must be a valid IPv4 address
        - Log directory will be created if it doesn't exist
    """
    config = {}
    
    # 1.1.1.1: API Key (REQUIRED - no default)
    api_key = os.getenv("WOL_API_KEY")
    if not api_key:
        raise ValueError(
            "FATAL: WOL_API_KEY environment variable not set. "
            "Please set WOL_API_KEY with a strong API key (min 20 chars)."
        )
    
    # Validate API key strength (min 20 chars, max 256 chars)
    if len(api_key) < 20:
        raise ValueError(
            "FATAL: WOL_API_KEY is too short. "
            "Minimum 20 characters required for security."
        )
    if len(api_key) > 256:
        raise ValueError(
            "FATAL: WOL_API_KEY is too long. "
            "Maximum 256 characters allowed."
        )
    config["API_KEY"] = api_key
    
    # 1.1.1.2: Broadcast IP (defaults to standard LAN broadcast)
    broadcast_ip = os.getenv("BROADCAST_IP", "10.10.10.255")
    # Basic validation: ensure it looks like an IP and ends in .255 (broadcast)
    if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", broadcast_ip):
        raise ValueError(
            f"FATAL: BROADCAST_IP '{broadcast_ip}' is not a valid IPv4 address."
        )
    config["BROADCAST_IP"] = broadcast_ip
    
    # 1.1.1.3: Log File (defaults to standard location)
    log_file = os.getenv("LOG_FILE", "/var/log/rustdesk-wol-proxy.log")
    # Ensure parent directory exists for log file
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError as e:
            raise ValueError(
                f"FATAL: Cannot create log directory '{log_dir}': {str(e)}"
            )
    config["LOG_FILE"] = log_file
    
    # 1.1.1.4: ID→MAC Mapping (ALLOWED_IDS)
    # This is the core configuration section with clear structure
    config["ALLOWED_IDS"] = {
        "123456789": "AA:BB:CC:DD:EE:FF",   # RustDesk ID → MAC
        "987654321": "11:22:33:44:55:66",
        # Add your real mappings here
    }
    
    return config

# Load configuration at startup
try:
    CONFIG = load_configuration()
    API_KEY = CONFIG["API_KEY"]
    BROADCAST_IP = CONFIG["BROADCAST_IP"]
    LOG_FILE = CONFIG["LOG_FILE"]
    ALLOWED_IDS = CONFIG["ALLOWED_IDS"]
except ValueError as e:
    print(f"Configuration Error: {e}")
    raise

# Create Flask app
app = Flask(__name__)

# ==============================
# 1.1.3 - LOGGING ENHANCEMENTS
# ==============================

class ContextualFilter(logging.Filter):
    """Filter that adds request context (remote_addr, request_id) to logs.
    
    This logging filter injects contextual information into each log record,
    including the client's remote IP address and a unique request ID. This
    enables comprehensive request tracing and per-client log analysis.
    
    Attributes:
        None
    
    Methods:
        filter: Add contextual attributes to log records.
    """

    def filter(self, record):
        """Add remote_addr and request_id to logging records.
        
        Injects the client IP address and request ID into each log record,
        enabling comprehensive request tracing across the application.
        
        Args:
            record (logging.LogRecord): The log record to enhance with context.
        
        Returns:
            bool: Always returns True to allow the record to be logged.
        
        Note:
            If request context is not available (e.g., during startup),
            uses "N/A" as placeholder values.
        """
        # Get remote IP address from Flask request context
        # Check if we're in a request context to avoid RuntimeError
        try:
            from flask import has_request_context
            if has_request_context():
                record.remote_addr = request.remote_addr
                record.request_id = request.environ.get("HTTP_X_REQUEST_ID", "N/A")
            else:
                record.remote_addr = "N/A"
                record.request_id = "N/A"
        except (RuntimeError, AttributeError):
            record.remote_addr = "N/A"
            record.request_id = "N/A"
        return True

# Configure rotating file handler with enhanced logging
try:
    handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=5*1024*1024,  # 5MB per file
        backupCount=3  # Keep 3 backup files (total ~20MB)
    )
    
    # Enhanced log format: includes timestamp, level, remote_addr, and message
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(remote_addr)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # Add contextual filter to inject remote_addr
    contextual_filter = ContextualFilter()
    handler.addFilter(contextual_filter)
    
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    
except Exception as e:
    print(f"Logging Configuration Error: {e}")
    raise

# ==============================
# HELPER FUNCTIONS
# ==============================

def mask_api_key(full_key):
    """Mask API key for safe logging and display.
    
    Creates a masked representation of an API key that shows only the first
    10 characters followed by "***", allowing identification while protecting
    the full key content in logs and error messages.
    
    Args:
        full_key (str): The complete API key to mask.
    
    Returns:
        str: Masked key in format "XXXXXXXXXX***" or "***" if key is shorter
             than 10 characters.
    
    Examples:
        >>> mask_api_key("wol_prod_secret123abc")
        'wol_prod_se***'
        >>> mask_api_key("short")
        '***'
    
    Note:
        This function is used in logging to prevent sensitive credentials
        from being exposed in security logs or monitoring systems.
    """
    if len(full_key) >= 10:
        return full_key[:10] + "***"
    return "***"


def validate_id_format(rustdesk_id):
    """Validate RustDesk ID parameter format.
    
    Validates that a RustDesk ID meets security and format requirements:
    - Must be non-empty
    - Maximum 50 characters
    - Alphanumeric characters only (no spaces, special characters)
    
    Args:
        rustdesk_id (str or None): The RustDesk ID to validate.
    
    Returns:
        tuple: A two-element tuple (is_valid, error_message) where:
            - is_valid (bool): True if ID is valid, False otherwise
            - error_message (str or None): Error description if invalid, None if valid
    
    Examples:
        >>> validate_id_format("123456789")
        (True, None)
        >>> validate_id_format(None)
        (False, 'ID parameter is required')
        >>> validate_id_format("id-with-special@chars")
        (False, 'ID parameter must contain only alphanumeric characters')
    
    Note:
        IDs are used to identify RustDesk devices in the system and must
        match configured device identifiers exactly.
    """
    if not rustdesk_id:
        return False, "ID parameter is required"
    
    if len(rustdesk_id) > 50:
        return False, f"ID parameter exceeds maximum length (50 chars, got {len(rustdesk_id)})"
    
    if not re.match(r"^[a-zA-Z0-9]+$", rustdesk_id):
        return False, "ID parameter must contain only alphanumeric characters"
    
    return True, None


def validate_api_key_format(api_key):
    """Validate API key parameter format.
    
    Validates that an API key meets security and format requirements:
    - Must be non-empty
    - Minimum 20 characters (security requirement)
    - Maximum 256 characters
    
    Args:
        api_key (str or None): The API key to validate.
    
    Returns:
        tuple: A two-element tuple (is_valid, error_message) where:
            - is_valid (bool): True if key is valid, False otherwise
            - error_message (str or None): Error description if invalid, None if valid
    
    Examples:
        >>> validate_api_key_format("wol_prod_1234567890")
        (False, 'API key is too short (min 20 chars, got 19)')
        >>> validate_api_key_format("wol_prod_12345678901234567890")
        (True, None)
        >>> validate_api_key_format(None)
        (False, 'API key parameter is required')
    
    Note:
        API keys must be sufficiently long to provide security. The 20-character
        minimum is a security best practice for this application.
    """
    if not api_key:
        return False, "API key parameter is required"
    
    if len(api_key) < 20:
        return False, f"API key is too short (min 20 chars, got {len(api_key)})"
    
    if len(api_key) > 256:
        return False, f"API key exceeds maximum length (256 chars, got {len(api_key)})"
    
    return True, None


def get_iso_timestamp():
    """Generate ISO 8601 UTC timestamp for API responses.
    
    Creates a properly formatted ISO 8601 timestamp in UTC timezone with
    millisecond precision, suitable for API response timestamps and logging.
    
    Returns:
        str: ISO 8601 formatted timestamp string (e.g., "2026-02-10T20:12:52.493Z")
    
    Examples:
        >>> timestamp = get_iso_timestamp()
        >>> len(timestamp)
        24
        >>> timestamp.endswith('Z')
        True
    
    Note:
        The 'Z' suffix indicates UTC timezone (Zulu time). Timestamps are
        generated server-side to ensure consistency across clients.
    """
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def generate_request_id():
    """Generate unique request ID for distributed request tracing.
    
    Creates a UUID4-based request identifier that is included in API responses
    and logs. This enables end-to-end request tracing across systems and helps
    correlate related log entries for debugging and monitoring.
    
    Returns:
        str: UUID4 string identifier (e.g., "f47ac10b-58cc-4372-a567-0e02b2c3d479")
    
    Examples:
        >>> req_id = generate_request_id()
        >>> len(req_id)
        36
        >>> req_id.count('-')
        4
    
    Note:
        Request IDs are sent in the X-Request-ID response header and included
        in all application logs for this request, enabling comprehensive tracing.
    """
    return str(uuid.uuid4())

# ==============================
# REQUEST/RESPONSE MIDDLEWARE
# ==============================

@app.before_request
def before_request_handler():
    """Generate request context for tracing and performance monitoring.
    
    This middleware runs before each request to initialize request context
    including a unique request ID for tracing and a start time for measuring
    request duration. These values are stored in Flask's g object which is
    request-scoped.
    
    Sets on flask.g:
        - request_id (str): UUID4 identifier for this request
        - start_time (float): Unix timestamp when request started
    
    Example:
        This function is called automatically by Flask for every request.
        Results are available via flask.g and response headers.
    
    Note:
        The request_id and duration are automatically added to all responses
        by the after_request handler.
    """
    # 1.1.5: Add unique request ID for tracing (X-Request-ID)
    g.request_id = generate_request_id()
    
    # 1.1.3: Track request start time for duration tracking
    g.start_time = time.time()


@app.after_request
def after_request(response):
    """Add tracing and performance headers to response.
    
    Middleware that runs after each request to append request tracking
    headers including the unique request ID and request duration. These
    headers enable end-to-end request tracing and performance monitoring.
    
    Args:
        response (flask.Response): The Flask response object to enhance.
    
    Returns:
        flask.Response: The same response object with added headers:
            - X-Request-ID: Unique identifier for tracing
            - X-Request-Duration-Ms: Request processing time in milliseconds
    
    Example:
        $ curl -i http://localhost:5001/health
        HTTP/1.1 200 OK
        X-Request-ID: f47ac10b-58cc-4372-a567-0e02b2c3d479
        X-Request-Duration-Ms: 5
    
    Note:
        This function is called automatically by Flask after each response
        is generated, before sending the response to the client.
    """
    response.headers["X-Request-ID"] = getattr(g, "request_id", "unknown")
    
    # Add request duration to response header
    if hasattr(g, "start_time"):
        duration = time.time() - g.start_time
        response.headers["X-Request-Duration-Ms"] = str(int(duration * 1000))
    
    return response

# ==============================
# ROUTES
# ==============================

@app.route('/wake', methods=['GET'])
def wake():
    """Send Wake-on-LAN magic packet to a registered device.
    
    Main API endpoint that handles WOL requests. Performs comprehensive
    validation of input parameters, authenticates the request via API key,
    looks up the target device's MAC address, and sends a magic packet on
    the configured broadcast network. All actions are logged for audit trails.
    
    Query Parameters:
        id (str): RustDesk device identifier. Required. Must be 1-50
            alphanumeric characters only. Used to look up the target MAC
            address in the configured device mappings.
        key (str): API authentication key. Required. Must be 20-256 characters.
            Validated against WOL_API_KEY for authentication before any
            WOL action is attempted.
    
    Returns:
        tuple: (response_dict, http_status_code) where response_dict contains:
            
        On Success (HTTP 200):
            {
                "status": "success",
                "code": "SEND_SUCCESS",
                "message": "Wake-on-LAN packet sent to <MAC>",
                "id": "123456789",
                "mac": "AA:BB:CC:DD:EE:FF",
                "timestamp": "2026-02-10T20:12:52.493Z"
            }
        
        On Error (HTTP 400/403/404/500):
            {
                "status": "error",
                "code": "<ERROR_CODE>",
                "message": "<ERROR_DESCRIPTION>",
                "timestamp": "2026-02-10T20:12:52.493Z"
            }
    
    Status Codes:
        200 - Successfully sent WOL magic packet
        400 - Missing or invalid parameters (ID format, key length)
        403 - Invalid API key (authentication failed)
        404 - Device ID not found in configured mappings
        500 - System error sending packet (permissions, network)
    
    Error Codes (in response):
        MISSING_PARAMETER - Required parameter (id or key) is missing
        INVALID_PARAMETER - Parameter format is invalid
        INVALID_KEY - API key doesn't match configured key
        UNKNOWN_ID - Device ID not found in ALLOWED_IDS mapping
        PERMISSION_DENIED - System permissions issue (not root/privileged)
        NETWORK_ERROR - Network unreachable or configuration error
        SEND_FAILED - Generic failure to send magic packet
    
    Examples:
        Success:
        >>> curl "http://localhost:5001/wake?id=123456789&key=wol_prod_KEYXXXXXXX"
        {"status":"success","code":"SEND_SUCCESS","message":"Wake-on-LAN packet...}
        
        Missing key:
        >>> curl "http://localhost:5001/wake?id=123456789"
        {"status":"error","code":"MISSING_PARAMETER","message":"Missing key...}
        
        Invalid key:
        >>> curl "http://localhost:5001/wake?id=123456789&key=wrongkey"
        {"status":"error","code":"INVALID_KEY","message":"Invalid API key...}
    
    Security:
        - API key is required and validated before any action
        - Invalid key attempts are logged for monitoring
        - API key is masked in logs to prevent exposure
        - Device MAC addresses are only revealed on successful auth
    
    Logging:
        - All requests logged with source IP address
        - Successful WOL sends logged at INFO level
        - Invalid keys logged at WARNING level (possible attack)
        - System errors logged at ERROR level
        - Request ID included in all log entries for tracing
    
    Note:
        The WOL magic packet is sent as a UDP broadcast on the configured
        BROADCAST_IP (default 10.10.10.255). Target devices must have
        WOL enabled in BIOS and be on the same network segment.
    """
    
    # Extract parameters
    client_api_key = request.args.get('key')
    rustdesk_id = request.args.get('id')
    
    timestamp = get_iso_timestamp()
    remote_addr = request.remote_addr
    
    # ===== 1.1.4 - INPUT VALIDATION =====
    
    # Check for missing ID parameter
    if not rustdesk_id:
        error_msg = "Missing id parameter"
        error_code = "MISSING_PARAMETER"
        app.logger.warning(f"[{remote_addr}] {error_msg}")
        return jsonify({
            "status": "error",
            "code": error_code,
            "message": error_msg,
            "timestamp": timestamp
        }), 400
    
    # Check for missing API key parameter
    if not client_api_key:
        error_msg = "Missing key parameter"
        error_code = "MISSING_PARAMETER"
        app.logger.warning(f"[{remote_addr}] {error_msg}")
        return jsonify({
            "status": "error",
            "code": error_code,
            "message": error_msg,
            "timestamp": timestamp
        }), 400
    
    # Validate ID format (alphanumeric, max 50 chars)
    is_valid_id, id_error = validate_id_format(rustdesk_id)
    if not is_valid_id:
        error_code = "INVALID_PARAMETER"
        app.logger.warning(
            f"[{remote_addr}] Invalid ID format: {id_error} (ID: {rustdesk_id})"
        )
        return jsonify({
            "status": "error",
            "code": error_code,
            "message": id_error,
            "timestamp": timestamp
        }), 400
    
    # Validate API key format (min 20, max 256 chars)
    is_valid_key_format, key_error = validate_api_key_format(client_api_key)
    if not is_valid_key_format:
        error_code = "INVALID_PARAMETER"
        app.logger.warning(
            f"[{remote_addr}] Invalid API key format: {key_error}"
        )
        return jsonify({
            "status": "error",
            "code": error_code,
            "message": key_error,
            "timestamp": timestamp
        }), 400
    
    # ===== AUTHENTICATION =====
    
    # Validate API key (exact match)
    if client_api_key != API_KEY:
        masked_key = mask_api_key(client_api_key)
        error_msg = "Invalid API key"
        error_code = "INVALID_KEY"
        app.logger.warning(
            f"[{remote_addr}] {error_msg} attempt (key: {masked_key}, ID: {rustdesk_id})"
        )
        # 1.1.4: Rate limiting placeholder - log for future monitoring
        app.logger.info(
            f"[{remote_addr}] Rate limit tracking: Invalid key attempt from IP"
        )
        return jsonify({
            "status": "error",
            "code": error_code,
            "message": error_msg,
            "timestamp": timestamp
        }), 403
    
    # ===== AUTHORIZATION =====
    
    # Lookup MAC address for RustDesk ID
    mac = ALLOWED_IDS.get(rustdesk_id)
    if not mac:
        error_msg = "No MAC address registered for this ID"
        error_code = "UNKNOWN_ID"
        app.logger.warning(
            f"[{remote_addr}] {error_msg} (ID: {rustdesk_id})"
        )
        return jsonify({
            "status": "error",
            "code": error_code,
            "message": error_msg,
            "timestamp": timestamp
        }), 404
    
    # ===== SEND MAGIC PACKET =====
    
    try:
        # Send magic packet
        # Note: wakeonlan.send_magic_packet sends to broadcast by default
        # The ip parameter specifies the broadcast address
        wakeonlan.send_magic_packet(mac, ip_address=BROADCAST_IP)
        
        # 1.1.5 - RESPONSE ENHANCEMENTS: Success response with timestamp and MAC
        masked_key = mask_api_key(client_api_key)
        app.logger.info(
            f"[{remote_addr}] WOL packet sent to {mac} (ID: {rustdesk_id}, key: {masked_key})"
        )
        
        return jsonify({
            "status": "success",
            "code": "SEND_SUCCESS",
            "message": f"Wake-on-LAN packet sent to {mac}",
            "id": rustdesk_id,
            "mac": mac,
            "timestamp": timestamp
        }), 200
    
    # ===== 1.1.2 - ERROR HANDLING =====
    
    except OSError as e:
        # 1.1.2: Handle permission errors (OSError with errno 1)
        error_msg = str(e)
        if "Operation not permitted" in error_msg or e.errno == 1:
            # Permission error - log as WARNING (likely a configuration issue)
            app.logger.warning(
                f"[{remote_addr}] Permission denied sending WOL to {mac} "
                f"(ID: {rustdesk_id}): {error_msg}"
            )
            return jsonify({
                "status": "error",
                "code": "PERMISSION_DENIED",
                "message": "Permission denied while sending magic packet. "
                           "Check system privileges and network configuration.",
                "timestamp": timestamp
            }), 500
        
        # 1.1.2: Handle network unreachability errors
        elif "Network is unreachable" in error_msg or e.errno == 101:
            app.logger.error(
                f"[{remote_addr}] Network unreachable sending WOL to {mac} "
                f"(ID: {rustdesk_id}): {error_msg}"
            )
            return jsonify({
                "status": "error",
                "code": "NETWORK_ERROR",
                "message": "Network is unreachable. Check network configuration.",
                "timestamp": timestamp
            }), 500
        
        # Other OS errors
        else:
            app.logger.error(
                f"[{remote_addr}] OS error sending WOL to {mac} "
                f"(ID: {rustdesk_id}): {error_msg}"
            )
            return jsonify({
                "status": "error",
                "code": "SEND_FAILED",
                "message": "Failed to send magic packet due to system error.",
                "timestamp": timestamp
            }), 500
    
    except Exception as e:
        # 1.1.2: General exception handling
        error_msg = str(e)
        app.logger.error(
            f"[{remote_addr}] Unexpected error sending WOL to {mac} "
            f"(ID: {rustdesk_id}): {error_msg}"
        )
        return jsonify({
            "status": "error",
            "code": "SEND_FAILED",
            "message": "Failed to send magic packet due to unexpected error.",
            "timestamp": timestamp
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for monitoring and status verification.
    
    Lightweight endpoint for performing health checks and monitoring the
    API server status. Returns immediately with server status and timestamp.
    No authentication required. Suitable for automated monitoring systems,
    load balancers, and Kubernetes health probes.
    
    Query Parameters:
        None - This endpoint requires no parameters.
    
    Returns:
        tuple: (response_dict, http_status_code) where response_dict is:
            {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2026-02-10T20:12:52.493Z"
            }
    
    Status Code:
        200 - Server is healthy and running
    
    Examples:
        >>> curl http://localhost:5001/health
        {"status":"healthy","version":"1.0.0","timestamp":"2026-02-10T20:12:52.493Z"}
        
        >>> curl -i http://localhost:5001/health
        HTTP/1.1 200 OK
        X-Request-ID: f47ac10b-58cc-4372-a567-0e02b2c3d479
        X-Request-Duration-Ms: 2
        Content-Length: 76
    
    Use Cases:
        - Kubernetes liveness/readiness probes
        - Load balancer health checks
        - Availability monitoring
        - Uptime verification
        - Connectivity testing
    
    Note:
        Health check does not perform database/cache checks as this is a
        stateless API. Server is healthy if it can respond to requests.
    """
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": get_iso_timestamp()
    }), 200


# ==============================
# ERROR HANDLERS
# ==============================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found HTTP errors.
    
    Error handler for requests to non-existent endpoints. Returns a
    standardized error response with error code and timestamp.
    
    Args:
        error (werkzeug.exceptions.NotFound): The 404 error exception.
    
    Returns:
        tuple: (response_dict, 404) where response_dict contains:
            {
                "status": "error",
                "code": "NOT_FOUND",
                "message": "Endpoint not found",
                "timestamp": "2026-02-10T20:12:52.493Z"
            }
    
    Example:
        >>> curl http://localhost:5001/invalid/endpoint
        {"status":"error","code":"NOT_FOUND","message":"Endpoint not found"...}
    """
    return jsonify({
        "status": "error",
        "code": "NOT_FOUND",
        "message": "Endpoint not found",
        "timestamp": get_iso_timestamp()
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 Method Not Allowed HTTP errors.
    
    Error handler for requests using unsupported HTTP methods. For example,
    POST to an endpoint that only accepts GET.
    
    Args:
        error (werkzeug.exceptions.MethodNotAllowed): The 405 error exception.
    
    Returns:
        tuple: (response_dict, 405) where response_dict contains:
            {
                "status": "error",
                "code": "METHOD_NOT_ALLOWED",
                "message": "HTTP method not allowed for this endpoint",
                "timestamp": "2026-02-10T20:12:52.493Z"
            }
    
    Example:
        >>> curl -X POST http://localhost:5001/health
        {"status":"error","code":"METHOD_NOT_ALLOWED"...}
    """
    return jsonify({
        "status": "error",
        "code": "METHOD_NOT_ALLOWED",
        "message": "HTTP method not allowed for this endpoint",
        "timestamp": get_iso_timestamp()
    }), 405


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server Error exceptions.
    
    Error handler for unhandled exceptions during request processing.
    Logs the error details and returns a standardized error response to
    the client without exposing internal details.
    
    Args:
        error (Exception): The unhandled exception that triggered this handler.
    
    Returns:
        tuple: (response_dict, 500) where response_dict contains:
            {
                "status": "error",
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "timestamp": "2026-02-10T20:12:52.493Z"
            }
    
    Note:
        Error details are logged server-side for debugging but not exposed
        to clients for security reasons.
    """
    app.logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        "status": "error",
        "code": "INTERNAL_ERROR",
        "message": "Internal server error",
        "timestamp": get_iso_timestamp()
    }), 500


# ==============================
# APPLICATION STARTUP
# ==============================

if __name__ == '__main__':
    """Application entry point for RustDesk WOL Proxy API.
    
    Initializes and starts the Flask application server. Logs startup
    configuration and starts listening on 0.0.0.0:5001 for incoming
    requests. Debug mode is disabled for production security.
    
    Environment Requirements:
        - WOL_API_KEY: Must be set before starting
        - BROADCAST_IP: Optional, defaults to 10.10.10.255
        - LOG_FILE: Optional, defaults to /var/log/rustdesk-wol-proxy.log
    
    Startup Output:
        Logs configuration details including:
        - Server address and port
        - Broadcast network address
        - Log file path
        - Number of registered devices
    
    Running:
        Server will listen on http://0.0.0.0:5001
        - /wake: WOL endpoint (GET)
        - /health: Health check endpoint (GET)
        - Debug mode: OFF (production environment)
        - Log level: INFO
    
    Stopping:
        Press Ctrl+C to stop the server gracefully.
    
    Note:
        This script should be run via Flask CLI or systemd service for
        production deployments. Direct execution is suitable for development.
    """
    # Log startup information
    app.logger.info(
        f"RustDesk WOL Proxy starting - API Server at 0.0.0.0:5001"
    )
    app.logger.info(
        f"Configuration: BROADCAST_IP={BROADCAST_IP}, LOG_FILE={LOG_FILE}"
    )
    app.logger.info(
        f"Allowed IDs configured: {len(ALLOWED_IDS)} device(s)"
    )
    
    # 1.1.5 - RESPONSE ENHANCEMENTS: Disable debug mode for production security
    app.run(host='0.0.0.0', port=5001, debug=False)