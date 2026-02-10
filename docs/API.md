# RustDesk WOL Proxy API Documentation

## Overview

The RustDesk WOL Proxy API is a RESTful service that provides Wake-on-LAN (WOL) functionality for RustDesk-managed computers. It handles authentication, device lookup, and magic packet transmission to wake computers on a network.

**Current Version**: 1.0.0  
**Base URL**: `http://<server>:5001`  
**Protocol**: HTTP (REST/JSON)  
**Authentication**: API Key (query parameter)

---

## Table of Contents

1. [Authentication](#authentication)
2. [API Endpoints](#api-endpoints)
3. [Response Format](#response-format)
4. [Error Codes](#error-codes)
5. [Examples](#examples)
6. [Configuration](#configuration)
7. [Security Considerations](#security-considerations)

---

## Authentication

All requests to the `/wake` endpoint require API key authentication via the `key` query parameter.

### API Key Requirements

- **Minimum Length**: 20 characters
- **Maximum Length**: 256 characters
- **Format**: Any alphanumeric string (recommended: `wol_prod_<random_string>`)
- **Storage**: Environment variable `WOL_API_KEY`

### Authentication Failure

Invalid API keys return HTTP 403 with error code `INVALID_KEY`. Invalid key attempts are logged for security monitoring.

### Health Endpoint

The `/health` endpoint does NOT require authentication and can be accessed without an API key.

---

## API Endpoints

### 1. Wake-on-LAN Endpoint

**Endpoint**: `/wake`  
**Method**: `GET`  
**Authentication**: Required (API key)

#### Request

```
GET /wake?id=<device_id>&key=<api_key>
```

#### Query Parameters

| Parameter | Required | Type | Constraints | Description |
|-----------|----------|------|-------------|-------------|
| `id` | Yes | String | 1-50 alphanumeric chars | RustDesk device identifier |
| `key` | Yes | String | 20-256 chars | API authentication key |

#### Response Format

**Success (HTTP 200)**:
```json
{
  "status": "success",
  "code": "SEND_SUCCESS",
  "message": "Wake-on-LAN packet sent to AA:BB:CC:DD:EE:FF",
  "id": "123456789",
  "mac": "AA:BB:CC:DD:EE:FF",
  "timestamp": "2026-02-10T20:12:52.493Z"
}
```

**Error (HTTP 4xx/5xx)**:
```json
{
  "status": "error",
  "code": "<ERROR_CODE>",
  "message": "<ERROR_DESCRIPTION>",
  "timestamp": "2026-02-10T20:12:52.493Z"
}
```

#### HTTP Status Codes

| Status | Meaning | Condition |
|--------|---------|-----------|
| 200 | OK | Magic packet sent successfully |
| 400 | Bad Request | Missing or invalid parameters |
| 403 | Forbidden | Invalid API key |
| 404 | Not Found | Device ID not in mapping |
| 500 | Server Error | System error sending packet |

#### Example Requests

**Valid Request**:
```bash
curl "http://localhost:5001/wake?id=123456789&key=wol_prod_example_key_1234567890"
```

**Missing Device ID**:
```bash
curl "http://localhost:5001/wake?key=wol_prod_example_key_1234567890"
```

**Invalid Key**:
```bash
curl "http://localhost:5001/wake?id=123456789&key=wrongkey"
```

---

### 2. Health Check Endpoint

**Endpoint**: `/health`  
**Method**: `GET`  
**Authentication**: Not required

#### Request

```
GET /health
```

#### Query Parameters

None - This endpoint takes no parameters.

#### Response

**Success (HTTP 200)**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-10T20:12:52.493Z"
}
```

#### HTTP Status Code

| Status | Meaning |
|--------|---------|
| 200 | Server is healthy |

#### Example Request

```bash
curl http://localhost:5001/health
```

#### Use Cases

- Kubernetes liveness probes
- Load balancer health checks
- Uptime monitoring
- Connectivity verification

---

## Response Format

### Standard Response Headers

All responses include the following headers for request tracing:

```
X-Request-ID: f47ac10b-58cc-4372-a567-0e02b2c3d479
X-Request-Duration-Ms: 42
```

| Header | Description |
|--------|-------------|
| `X-Request-ID` | Unique UUID for request tracing |
| `X-Request-Duration-Ms` | Request processing time in milliseconds |

### Timestamp Format

All timestamps in responses use ISO 8601 format with UTC timezone:

```
2026-02-10T20:12:52.493Z
```

- **T**: Separator between date and time
- **Z**: UTC timezone indicator (Zulu time)
- **Millisecond precision**: .493

---

## Error Codes

### Parameter Validation Errors (HTTP 400)

| Code | Message | Cause |
|------|---------|-------|
| `MISSING_PARAMETER` | Missing id parameter<br/>Missing key parameter | Required parameter is not provided |
| `INVALID_PARAMETER` | ID parameter exceeds maximum length<br/>ID must be alphanumeric<br/>API key too short/long | Parameter format constraints violated |

### Authentication Errors (HTTP 403)

| Code | Message | Cause |
|------|---------|-------|
| `INVALID_KEY` | Invalid API key | Provided key doesn't match configured API key |

### Not Found Errors (HTTP 404)

| Code | Message | Cause |
|------|---------|-------|
| `UNKNOWN_ID` | No MAC address registered for this ID | Device ID not found in ALLOWED_IDS mapping |
| `NOT_FOUND` | Endpoint not found | Non-existent endpoint requested |

### Server Errors (HTTP 500)

| Code | Message | Cause |
|------|---------|-------|
| `PERMISSION_DENIED` | Permission denied while sending magic packet | Process lacks privileges (not running as root/ubuntu) |
| `NETWORK_ERROR` | Network is unreachable | Network configuration error or no route to broadcast |
| `SEND_FAILED` | Failed to send magic packet | Generic WOL transmission failure |
| `INTERNAL_ERROR` | Internal server error | Unhandled application exception |

### HTTP Method Errors (HTTP 405)

| Code | Message | Cause |
|------|---------|-------|
| `METHOD_NOT_ALLOWED` | HTTP method not allowed | Wrong HTTP method for endpoint (e.g., POST to /wake) |

---

## Examples

### Example 1: Successful WOL Request

**Request**:
```bash
curl -i "http://localhost:5001/wake?id=123456789&key=wol_prod_securekey1234567890"
```

**Response**:
```
HTTP/1.1 200 OK
X-Request-ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
X-Request-Duration-Ms: 8
Content-Type: application/json

{
  "status": "success",
  "code": "SEND_SUCCESS",
  "message": "Wake-on-LAN packet sent to AA:BB:CC:DD:EE:FF",
  "id": "123456789",
  "mac": "AA:BB:CC:DD:EE:FF",
  "timestamp": "2026-02-10T20:12:52.493Z"
}
```

### Example 2: Missing API Key

**Request**:
```bash
curl -i "http://localhost:5001/wake?id=123456789"
```

**Response**:
```
HTTP/1.1 400 Bad Request
X-Request-ID: b2c3d4e5-f6a7-8901-bcde-f12345678901
X-Request-Duration-Ms: 2
Content-Type: application/json

{
  "status": "error",
  "code": "MISSING_PARAMETER",
  "message": "Missing key parameter",
  "timestamp": "2026-02-10T20:12:52.600Z"
}
```

### Example 3: Invalid API Key

**Request**:
```bash
curl -i "http://localhost:5001/wake?id=123456789&key=wrongkey"
```

**Response**:
```
HTTP/1.1 403 Forbidden
X-Request-ID: c3d4e5f6-a7b8-9012-cdef-123456789012
X-Request-Duration-Ms: 3
Content-Type: application/json

{
  "status": "error",
  "code": "INVALID_KEY",
  "message": "Invalid API key",
  "timestamp": "2026-02-10T20:12:52.700Z"
}
```

### Example 4: Device ID Not Found

**Request**:
```bash
curl -i "http://localhost:5001/wake?id=wrongid&key=wol_prod_securekey1234567890"
```

**Response**:
```
HTTP/1.1 404 Not Found
X-Request-ID: d4e5f6a7-b8c9-0123-def0-1234567890ab
X-Request-Duration-Ms: 2
Content-Type: application/json

{
  "status": "error",
  "code": "UNKNOWN_ID",
  "message": "No MAC address registered for this ID",
  "timestamp": "2026-02-10T20:12:52.800Z"
}
```

### Example 5: Health Check

**Request**:
```bash
curl -i "http://localhost:5001/health"
```

**Response**:
```
HTTP/1.1 200 OK
X-Request-ID: e5f6a7b8-c9d0-1234-ef01-23456789abc
X-Request-Duration-Ms: 2
Content-Type: application/json

{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-10T20:12:52.900Z"
}
```

### Example 6: Invalid ID Format

**Request**:
```bash
curl -i "http://localhost:5001/wake?id=invalid@id&key=wol_prod_securekey1234567890"
```

**Response**:
```
HTTP/1.1 400 Bad Request
X-Request-ID: f6a7b8c9-d0e1-2345-f012-3456789abc12
X-Request-Duration-Ms: 2
Content-Type: application/json

{
  "status": "error",
  "code": "INVALID_PARAMETER",
  "message": "ID parameter must contain only alphanumeric characters",
  "timestamp": "2026-02-10T20:12:53.000Z"
}
```

---

## Configuration

### Environment Variables

The API is configured via environment variables:

#### WOL_API_KEY (Required)

- **Description**: API authentication key
- **Type**: String
- **Min Length**: 20 characters
- **Max Length**: 256 characters
- **Example**: `wol_prod_securekey1234567890`
- **Validation**: Checked at startup; app won't start without valid key

#### BROADCAST_IP (Optional)

- **Description**: Network broadcast address for WOL packets
- **Type**: IPv4 address
- **Default**: `10.10.10.255`
- **Example**: `192.168.1.255`
- **Notes**: Must be valid IPv4; must be broadcast address for your subnet

#### LOG_FILE (Optional)

- **Description**: Path to application log file
- **Type**: File path
- **Default**: `/var/log/rustdesk-wol-proxy.log`
- **Example**: `/var/log/wol.log`
- **Notes**: Directory must exist or be creatable by the app process

### Device Configuration (ALLOWED_IDS)

Device ID to MAC address mappings are configured in the application code:

```python
ALLOWED_IDS = {
    "123456789": "AA:BB:CC:DD:EE:FF",   # Device name: RustDesk ID
    "987654321": "11:22:33:44:55:66",   # Another device
}
```

To add devices:
1. Edit `app.py`
2. Add entry to `ALLOWED_IDS` dictionary
3. Restart the service
4. Verify with `/health` endpoint

---

## Security Considerations

### API Key Security

1. **Strong Keys**: API keys must be at least 20 characters
   - Recommended: Use cryptographically random keys
   - Example generation: `python3 -c "import secrets; print('wol_prod_' + secrets.token_hex(16))"`

2. **Key Storage**: 
   - Store in `.env` file (development only)
   - For production: Use systemd EnvironmentFile or key management system
   - Never commit keys to git

3. **Key Rotation**:
   - Periodically change API keys
   - Update all clients when key changes
   - Monitor for unauthorized key usage

### Network Security

1. **Firewall Rules**: Restrict port 5001 access
   - Only allow trusted clients (RustDesk server IP)
   - Block external internet access
   - Use internal network only

2. **HTTPS/TLS**:
   - Current implementation: HTTP only
   - For production: Deploy behind reverse proxy with HTTPS (nginx, Apache)
   - Use TLS certificates for encrypted transport

3. **Rate Limiting**:
   - Use reverse proxy for rate limiting
   - Monitor for brute force attempts
   - Block abusive clients

### Logging & Monitoring

1. **Log Location**: `/var/log/rustdesk-wol-proxy.log`
   - Contains all requests (source IP, device ID)
   - Failed authentication attempts logged at WARNING level
   - Useful for security auditing

2. **Request Tracing**:
   - Every request has unique X-Request-ID header
   - Use for correlating logs across systems
   - Helpful for troubleshooting and forensics

3. **Monitoring**:
   - Use `/health` endpoint for availability monitoring
   - Set up alerts for 500 errors in logs
   - Monitor for repeated failed authentication

### Operational Security

1. **Process Privileges**:
   - Run as dedicated `rustdesk-wol` user (not root if possible)
   - Requires raw socket capabilities for WOL
   - May need elevated privileges on some systems

2. **Access Control**:
   - Only authorized personnel should have API key
   - Use strong authentication for key management
   - Audit key access and rotation

3. **Device Mappings**:
   - Keep ALLOWED_IDS up to date
   - Remove decommissioned devices
   - Document which devices are registered

---

## Troubleshooting

### Common Issues

#### Server Won't Start

- **Check**: WOL_API_KEY environment variable is set and valid
- **Check**: Log file directory is writable
- **Check**: Port 5001 is not already in use

#### 403 Invalid Key

- **Check**: Ensure EXACT key match (case-sensitive)
- **Check**: Key is at least 20 characters
- **Check**: No extra spaces in key parameter

#### 404 Unknown ID

- **Check**: Device ID is registered in ALLOWED_IDS
- **Check**: Device ID is exact match (case-sensitive)
- **Check**: Device ID contains only alphanumeric characters

#### Network Error (HTTP 500)

- **Check**: Running with sufficient privileges (may need root)
- **Check**: Network interface is accessible
- **Check**: Target device is on same network segment

---

## Version History

### Version 1.0.0 (Current)

- ✅ WOL packet transmission
- ✅ API key authentication
- ✅ Request ID tracking
- ✅ Comprehensive error handling
- ✅ Rotating file logging
- ✅ Health check endpoint
- ✅ ISO 8601 timestamps

---

## Support

For issues or questions:

1. Check the logs: `tail -f /var/log/rustdesk-wol-proxy.log`
2. Review this documentation
3. Check ARCHITECTURE.md for deployment details
4. Review error codes and troubleshooting section above
