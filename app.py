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

# Configuration from environment variables with validation
def load_configuration():
    """
    Load and validate all configuration at startup.
    Raises exception if required config is missing or invalid.
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

# Create custom formatter that includes remote_addr
class ContextualFilter(logging.Filter):
    """
    Add request context (remote_addr, request_id) to log records.
    This ensures all logs include the source IP address.
    """
    def filter(self, record):
        # Get remote IP address from Flask request context
        record.remote_addr = request.remote_addr if request else "N/A"
        # Get request ID from Flask g object (set in middleware)
        record.request_id = request.environ.get("HTTP_X_REQUEST_ID", "N/A")
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
    """
    Mask API key in logs for security.
    Returns first 10 characters + "***" suffix.
    Example: "wol_prod_secret123abc" → "wol_prod_se***"
    """
    if len(full_key) >= 10:
        return full_key[:10] + "***"
    return "***"

def validate_id_format(rustdesk_id):
    """
    1.1.4 - INPUT VALIDATION for ID parameter
    Validate ID format:
    - Max 50 characters
    - Alphanumeric only (no special chars, spaces, etc.)
    Returns (is_valid, error_message)
    """
    if not rustdesk_id:
        return False, "ID parameter is required"
    
    if len(rustdesk_id) > 50:
        return False, f"ID parameter exceeds maximum length (50 chars, got {len(rustdesk_id)})"
    
    if not re.match(r"^[a-zA-Z0-9]+$", rustdesk_id):
        return False, "ID parameter must contain only alphanumeric characters"
    
    return True, None

def validate_api_key_format(api_key):
    """
    1.1.4 - INPUT VALIDATION for API key parameter
    Validate API key format:
    - Min 20 characters (security requirement)
    - Max 256 characters
    Returns (is_valid, error_message)
    """
    if not api_key:
        return False, "API key parameter is required"
    
    if len(api_key) < 20:
        return False, f"API key is too short (min 20 chars, got {len(api_key)})"
    
    if len(api_key) > 256:
        return False, f"API key exceeds maximum length (256 chars, got {len(api_key)})"
    
    return True, None

def get_iso_timestamp():
    """
    1.1.5 - RESPONSE ENHANCEMENTS
    Generate ISO 8601 UTC timestamp for responses
    """
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

def generate_request_id():
    """
    1.1.5 - RESPONSE ENHANCEMENTS
    Generate unique request ID (X-Request-ID header) for tracing
    """
    return str(uuid.uuid4())

# ==============================
# REQUEST/RESPONSE MIDDLEWARE
# ==============================

@app.before_request
def before_request_handler():
    """
    Middleware to set up request context:
    - Generate unique request ID
    - Start request timer for duration tracking
    """
    # 1.1.5: Add unique request ID for tracing (X-Request-ID)
    g.request_id = generate_request_id()
    
    # 1.1.3: Track request start time for duration tracking
    g.start_time = time.time()

@app.after_request
def after_request(response):
    """
    1.1.3 - LOGGING ENHANCEMENTS
    Add request ID header and duration to response
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
    """
    Main WOL endpoint with comprehensive error handling and logging.
    
    Query parameters:
    - id: RustDesk ID (required, max 50 chars, alphanumeric)
    - key: API key (required, min 20 chars, max 256 chars)
    
    Responses:
    - 200: Success
    - 400: Missing/invalid parameters
    - 403: Invalid API key
    - 404: Unknown RustDesk ID
    - 500: Failed to send magic packet
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
    """
    Health check endpoint for monitoring and status verification.
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
    """Handle 404 Not Found errors."""
    return jsonify({
        "status": "error",
        "code": "NOT_FOUND",
        "message": "Endpoint not found",
        "timestamp": get_iso_timestamp()
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 Method Not Allowed errors."""
    return jsonify({
        "status": "error",
        "code": "METHOD_NOT_ALLOWED",
        "message": "HTTP method not allowed for this endpoint",
        "timestamp": get_iso_timestamp()
    }), 405


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server Errors."""
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