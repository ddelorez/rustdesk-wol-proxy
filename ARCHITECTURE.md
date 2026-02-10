# RustDesk Auto-WOL: Comprehensive Architecture & Gameplan

**Document Date:** 2026-02-10  
**Status:** Architecture Analysis Complete  
**Target Environment:** Self-hosted RustDesk @ 10.10.10.145/24  
**Project Phase:** Phase 1 (Backend API) In Progress

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [System Architecture](#system-architecture)
4. [Component Specifications](#component-specifications)
5. [API Specification](#api-specification)
6. [Security Architecture](#security-architecture)
7. [Deployment Architecture](#deployment-architecture)
8. [Phase 1 Implementation Gameplan](#phase-1-implementation-gameplan)
9. [Phase 2 Considerations (Client Integration)](#phase-2-considerations-client-integration)
10. [Testing & Validation Strategy](#testing--validation-strategy)
11. [Risk Analysis & Mitigation](#risk-analysis--mitigation)
12. [Development Roadmap](#development-roadmap)

---

## Executive Summary

The RustDesk Auto-WOL project solves the inability for offsite users to wake sleeping machines in a self-hosted RustDesk environment. The solution architecture consists of three integrated components:

1. **WOL Proxy API** (Phase 1): A lightweight Flask/gunicorn service running on the RustDesk server that accepts wake requests and sends magic packets to targets
2. **Custom RustDesk Client** (Phase 2): A forked RustDesk client that detects offline peers and automatically invokes WOL
3. **Configuration & Orchestration** (Ongoing): Secure delivery of API keys, ID↔MAC mappings, and deployment automation

**Key Innovation:** By centralizing WOL on the RustDesk server (which sits on the target LAN), we enable offsite clients to wake machines without requiring internet-accessible broadcast protocols.

---

## Problem Statement

### Current Limitations

RustDesk's built-in Wake-on-LAN feature operates only within local LANs. When attempting WOL from an offsite client:

- **Issue**: Magic packets (UDP broadcast to port 9) cannot route from internet to LAN
- **Result**: Offsite users cannot wake sleeping machines; connections fail
- **Workaround**: Requires manual intervention or complex VPN configurations

### Design Constraints

- **Network topology**: Single LAN (10.10.10.0/24), RustDesk server at 10.10.10.145
- **User base**: Mix of LAN and offsite clients connecting to shared RustDesk server
- **Scope**: Target 5-20 machines initially; expandable to larger deployments
- **Security**: API must not expose machine information or enable unauthorized wakeups

### Acceptance Criteria

- ✓ Offsite clients can wake sleeping machines via single API call
- ✓ Process completes within 2-3 minutes (wake + boot + RustDesk registration)
- ✓ Authorization enforced via shared secret (API key)
- ✓ Audit trail available (logging of all wake requests)
- ✓ Zero modifications to RustDesk server binaries (pure add-on service)

---

## System Architecture

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  [Offsite User] → [RustDesk Client (Custom Fork)]              │
│                                                                 │
│       Connection attempt to ID:XXXX fails (machine offline)     │
│       ↓                                                          │
│       Client detects offline status                             │
│       ↓                                                          │
│       HTTP GET /wake?id=XXXX&key=SECRET_KEY                    │
│                     ↓ (over internet/LAN)                       │
│       ┌───────────────────────────────────────────────┐        │
│       │                                               │        │
│       │  [RustDesk WOL Proxy API]                     │        │
│       │  (Flask + gunicorn @ 10.10.10.145:5001)     │        │
│       │                                               │        │
│       │  • Validate API key                          │        │
│       │  • Lookup MAC address for ID                 │        │
│       │  • Send magic packet                         │        │
│       │  • Log request + response                    │        │
│       │                                               │        │
│       └───────────────────────────────────────────────┘        │
│                     ↓                                           │
│       Magic packet sent to 10.10.10.255:9 (LAN broadcast)      │
│                     ↓                                           │
│       [Target Machine] receives magic packet                    │
│       ↓                                                          │
│       Machine boots + RustDesk service starts                   │
│       ↓                                                          │
│       RustDesk daemon registers with hbbs (signal server)       │
│       ↓                                                          │
│       [Offsite Client] retries connection → SUCCESS            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Architectural Layers

#### Layer 1: Client Integration (Phase 2)
- **Component**: Custom RustDesk Client Fork
- **Responsibility**: Detect offline connections, invoke WOL API, manage retry logic
- **Interface**: Configuration panel (API URL, API key), automatic detection logic

#### Layer 2: API & Business Logic (Phase 1)
- **Component**: Flask Application (app.py)
- **Responsibility**: Request validation, authentication, MAC mapping, logging
- **Interface**: RESTful HTTP endpoint (`/wake`)

#### Layer 3: Network & WOL (Phase 1)
- **Component**: WakeOnLAN Library + System Network Stack
- **Responsibility**: Construct and send magic packets via broadcast address
- **Interface**: System UDP socket for broadcast

#### Layer 4: Infrastructure & Deployment (Phase 1)
- **Component**: Systemd service, gunicorn WSGI server, virtual environment
- **Responsibility**: Process management, auto-restart, resource isolation
- **Interface**: systemd service control, environment variables

#### Layer 5: Security & Access Control (Phase 1)
- **Component**: API key validation, rate limiting, HTTPS proxy
- **Responsibility**: Prevent unauthorized access, mitigate abuse
- **Interface**: Nginx/Caddy reverse proxy (future), request headers

### Communication Patterns

| Pattern | Direction | Protocol | Purpose |
|---------|-----------|----------|---------|
| Client → API | Outbound (internet) | HTTPS/HTTP | WOL request with credentials |
| API → LAN Broadcast | Inbound (LAN) | UDP:9 | Magic packet transmission |
| API → Logging | Local | File I/O | Audit trail |
| Monitoring → API | Inbound | HTTP (health) | Service status checks |

---

## Component Specifications

### Component 1: WOL Proxy API

**Type**: Lightweight Python REST API  
**Framework**: Flask 3.0.3  
**Runtime**: gunicorn 23.0.0 (WSGI server)  
**Language**: Python 3.8+

**Responsibilities**:
- Accept HTTP requests to `/wake` endpoint
- Validate API key from query parameters
- Lookup RustDesk ID → MAC address mapping
- Construct and send magic packets
- Log all requests and responses with timestamps
- Return structured JSON responses

**Configuration**:
- API Key: Loaded from environment variable `WOL_API_KEY`
- Allowed IDs: Loaded from configuration (dict mapping ID → MAC)
- Broadcast IP: Configurable, default `10.10.10.255`
- Log File: `/var/log/rustdesk-wol-proxy.log` (rotating, 5MB max per file, 3 backups)
- Port: 5001 (exposed internally, proxied externally)

**Dependencies**:
```
Flask==3.0.3              # Web framework
gunicorn==23.0.0          # WSGI server
wakeonlan==3.1.0          # Magic packet library
python-json-logger==2.0.7 # Structured logging
python-dotenv==1.0.1      # .env file support
```

### Component 2: Configuration Management

**ID ↔ MAC Mapping Source**:
- Static dictionary in `app.py` (Phase 1)
- Future: External database or configuration file

**API Key Management**:
- Environment variable `WOL_API_KEY`
- Loaded at application startup
- Override via `.env` file (for development)
- Set via systemd service (`EnvironmentFile=`)

**Broadcast Address**:
- Hardcoded to `10.10.10.255` (LAN broadcast)
- Future: Make configurable for multi-LAN deployments

### Component 3: Systemd Service

**Service Name**: `rustdesk-wol.service`  
**Installation Path**: `/etc/systemd/system/rustdesk-wol.service`

**Key Features**:
- Auto-restart on failure
- Resource limits (CPU, memory)
- Standard output/error logging to journal
- User isolation (run as dedicated user)
- Socket activation (future enhancement)

**Configuration**:
- Working Directory: `/opt/rustdesk-wol-proxy`
- Environment File: `/opt/rustdesk-wol-proxy/.env`
- User: `rustdesk-wol` (dedicated system user)
- Group: `rustdesk-wol`

### Component 4: Logging & Auditing

**Log Destination**: `/var/log/rustdesk-wol-proxy.log`

**Log Format**:
```
2026-02-10 14:23:45,123 INFO: WOL packet sent to AA:BB:CC:DD:EE:FF (ID: 123456789) [in app.py:55]
2026-02-10 14:24:12,456 WARNING: Invalid API key attempt for ID 987654321 [in app.py:45]
2026-02-10 14:25:01,789 ERROR: Failed to send WOL packet to 11:22:33:44:55:66: [Errno 1] Operation not permitted [in app.py:62]
```

**Retention**: Rotating file handler (5 MB per file, 3 backup files = 20 MB max)

**Log Levels**:
- **INFO**: Successful WOL packet transmission
- **WARNING**: Invalid credentials, missing parameters, unknown IDs
- **ERROR**: Network failures, permission issues, exceptions

**Audit Requirements** (Phase 1 MVP):
- ✓ Request timestamp
- ✓ Requesting IP address (via Flask request context)
- ✓ API key used (do NOT log full key, only hash/indicator)
- ✓ RustDesk ID requested
- ✓ MAC address targeted
- ✓ Success/failure status
- ✓ Error messages (if failed)

---

## API Specification

### Endpoint: Wake Machine

**Request**:
```
GET /wake?id=<rustdesk_id>&key=<api_key>
```

**Parameters**:

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `id` | string | Yes | RustDesk global ID of target machine | `123456789` |
| `key` | string | Yes | API authentication key | `secret-key-xyz` |

**Query String Example**:
```
http://10.10.10.145:5001/wake?id=123456789&key=secret-key-xyz
```

**Success Response (HTTP 200)**:
```json
{
  "status": "success",
  "message": "Wake-on-LAN packet sent to AA:BB:CC:DD:EE:FF",
  "id": "123456789",
  "timestamp": "2026-02-10T14:23:45.123Z",
  "mac": "AA:BB:CC:DD:EE:FF"
}
```

**Error Responses**:

| Status | Code | Condition | Response |
|--------|------|-----------|----------|
| 400 | `MISSING_PARAMETER` | Missing `id` or `key` | `{"error": "Missing id/key parameter"}` |
| 403 | `INVALID_KEY` | API key does not match | `{"error": "Invalid API key"}` |
| 404 | `UNKNOWN_ID` | ID not in ALLOWED_IDS mapping | `{"error": "No MAC address registered for this ID"}` |
| 500 | `SEND_FAILED` | Exception sending magic packet | `{"error": "Failed to send magic packet"}` |

**Response Headers**:
```
Content-Type: application/json
X-Request-ID: <unique-request-id>  (future: for tracing)
X-RateLimit-Remaining: <count>     (future: rate limiting)
```

### Endpoint: Health Check (Future Enhancement)

**Request**:
```
GET /health
```

**Response (HTTP 200)**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 12345
}
```

---

## Security Architecture

### Authentication & Authorization

**API Key Strategy**:
- **Mechanism**: Single shared secret (query parameter `key`)
- **Distribution**: Embedded in custom RustDesk client binary / configuration
- **Constraints**: 
  - Must be strong (32+ characters, alphanumeric + special)
  - Rotatable (change in .env, restart service)
  - Never logged in full (only indicators)
  - Environment-specific (dev/test/prod)

**Alternatives Considered**:
- HMAC-SHA256 signing: Adds complexity without significant gain for internal API
- JWT tokens: Better for multi-tenant; overkill for single organization
- mTLS certificates: Would require client certificate distribution (future enhancement)

**Recommended Phase 1 API Key Format**:
```
wol_prod_<random_32_chars_base64>
```

Example:
```
wol_prod_x9kJ2mL8nP3qR5sT7uV9wX1yZ4aB6cD8
```

### Network Security

**Current State** (Phase 1):
- API runs on internal LAN (10.10.10.145:5001)
- Magic packets routed via LAN broadcast (0.0.0.0 → 10.10.10.255:9)
- Access from external networks: NOT ENABLED (Phase 1 scope)

**Future Exposure (Phase 2+)**:
- Reverse proxy (Nginx/Caddy) in front of Flask
- HTTPS/TLS encryption for client communication
- Rate limiting at proxy layer
- IP allowlisting for external clients

**Magic Packet Security**:
- Magic packets inherently broadcast on LAN (cannot be encrypted)
- Target MAC address is NOT secret (easily discoverable via network scanning)
- Threat model: Prevent unauthorized WOL invocation, not protect packet contents

### Access Control

**ID → MAC Mapping Storage** (Phase 1):
- Static Python dictionary in `app.py`
- Only administrators edit mapping
- No versioning/control within app itself
- **Future**: Git-tracked config file or database

**Rate Limiting** (Phase 1: Not Implemented):
- Plan: Implement in Phase 2 or via reverse proxy
- Strategy: Per-IP throttling (e.g., max 10 requests/minute)
- Rationale: Prevent DoS attacks, accidental misuse

### Input Validation

**ID Parameter**:
- Type: String (alphanumeric, 6-20 characters typical)
- Validation: Whitelist against ALLOWED_IDS keys
- Max length: 50 characters
- Reject: Anything not in mapping (prevent enumeration attacks)

**API Key Parameter**:
- Type: String (minimum 20 characters recommended)
- Validation: Exact match (case-sensitive) against API_KEY
- Max length: 256 characters
- Reject: Expired or invalid keys (log attempt)

**Broadcast IP**:
- Type: IPv4 address (hardcoded in Phase 1)
- Validation: Must be network broadcast address (*.255)
- Future: Address validation if made configurable

### Audit & Logging

**What Is Logged** (All WOL attempts):
- Timestamp (ISO 8601 UTC)
- Source IP address (from Flask `request.remote_addr`)
- API key indicator (first 10 chars + "***" suffix, never full key)
- RustDesk ID requested
- MAC address targeted
- Status (success/failure)
- Error details (if failed)

**What Is NOT Logged**:
- Full API key values
- Private machine names or sensitive data
- Network passwords or credentials

**Audit Trail Retention**:
- 20 MB total (3 × 5MB rotated files)
- Approximately 2-3 weeks of logs at 10-20 requests/day
- Manual archival for longer retention

**Future Enhancements**:
- Structured JSON logging (python-json-logger already in requirements)
- Centralized log aggregation (ELK, Splunk, etc.)
- Real-time alerting for suspicious patterns

### Threat Model & Mitigations

| Threat | Attack Vector | Impact | Mitigation (Phase 1) | Mitigation (Future) |
|--------|---|---|---|---|
| Unauthorized WOL | Wrong API key | Machine woken at wrong time | Strong API key, logging | Rate limiting, mTLS |
| DoS (WOL flooding) | Repeated requests to same ID | Resource exhaustion, broadcast spam | Logging detection | Rate limiting, IP blocks |
| API Key leakage | Compromised client binary | Full API access | Key rotation, short lifespan | Key versioning, rotation policy |
| Information disclosure | Enumeration of ID/MAC mappings | Network topology revealed | Reject unknown IDs silently | Implement 404-only responses |
| Network interception | Man-in-the-middle (HTTP) | API key/ID exposure | Internal LAN only | HTTPS/TLS encryption |
| Privilege escalation | Root access to service | Full system compromise | Dedicated user account | SELinux policies |

---

## Deployment Architecture

### Installation & Setup

**Prerequisites**:
- Linux server (Ubuntu 20.04+, Debian 11+, or equivalent)
- Python 3.8+ installed
- Root or sudo access for systemd setup
- Write access to `/opt` and `/var/log`

**Installation Steps**:

1. **Create application directory**:
   ```bash
   sudo mkdir -p /opt/rustdesk-wol-proxy
   sudo chown ubuntu:ubuntu /opt/rustdesk-wol-proxy  # adjust user as needed
   ```

2. **Clone repository**:
   ```bash
   cd /opt/rustdesk-wol-proxy
   git clone https://github.com/ddelore/rustdesk-wol-proxy .
   ```

3. **Create Python virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env  # (create template in repo)
   # Edit .env with:
   WOL_API_KEY=wol_prod_<strong_random_key>
   BROADCAST_IP=10.10.10.255
   LOG_FILE=/var/log/rustdesk-wol-proxy.log
   ```

5. **Create log directory and rotate config**:
   ```bash
   sudo mkdir -p /var/log/rustdesk-wol
   sudo touch /var/log/rustdesk-wol-proxy.log
   sudo chown nobody:nogroup /var/log/rustdesk-wol-proxy.log
   sudo chmod 0644 /var/log/rustdesk-wol-proxy.log
   ```

6. **Create systemd service**:
   ```bash
   sudo cp rustdesk-wol.service /etc/systemd/system/
   sudo systemctl daemon-reload
   ```

7. **Create dedicated user (optional but recommended)**:
   ```bash
   sudo useradd -r -s /bin/false rustdesk-wol
   sudo chown -R rustdesk-wol:rustdesk-wol /opt/rustdesk-wol-proxy
   sudo chown rustdesk-wol:rustdesk-wol /var/log/rustdesk-wol-proxy.log
   ```

8. **Enable and start service**:
   ```bash
   sudo systemctl enable rustdesk-wol.service
   sudo systemctl start rustdesk-wol.service
   sudo systemctl status rustdesk-wol.service
   ```

### Systemd Service File

**File**: `/etc/systemd/system/rustdesk-wol.service`

```ini
[Unit]
Description=RustDesk WOL Proxy API
Documentation=https://github.com/ddelore/rustdesk-wol-proxy
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
User=rustdesk-wol
Group=rustdesk-wol
WorkingDirectory=/opt/rustdesk-wol-proxy
Environment="PATH=/opt/rustdesk-wol-proxy/venv/bin"
EnvironmentFile=/opt/rustdesk-wol-proxy/.env
ExecStart=/opt/rustdesk-wol-proxy/venv/bin/gunicorn \
    --workers 2 \
    --worker-class sync \
    --bind 0.0.0.0:5001 \
    --timeout 30 \
    --access-logfile - \
    --error-logfile - \
    app:app

# Resource limits
MemoryLimit=256M
CPUQuota=50%

# Restart policy
Restart=on-failure
RestartSec=10

# Security hardening (Phase 2)
# PrivateTmp=yes
# NoNewPrivileges=yes
# ProtectSystem=strict
# ProtectHome=yes

[Install]
WantedBy=multi-user.target
```

### Reverse Proxy Configuration (When Needed)

**Nginx Example** (for external exposure via HTTPS):

```nginx
server {
    listen 443 ssl http2;
    server_name rustdesk-wol.example.com;

    ssl_certificate /etc/letsencrypt/live/rustdesk-wol.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/rustdesk-wol.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=wol_limit:10m rate=10r/m;
    limit_req zone=wol_limit burst=5 nodelay;

    location /wake {
        limit_req zone=wol_limit burst=5 nodelay;
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 10s;
    }
}
```

### Database / Persistent Storage (Future)

**Phase 2 Consideration**: Move ID ↔ MAC mapping to a lightweight database:
- **Option 1**: SQLite (no external dependency)
- **Option 2**: Redis (if caching is beneficial)
- **Option 3**: Git-tracked YAML/JSON config file

**Benefits**:
- No code redeployment to add machines
- Version control audit trail
- Multi-environment support

---

## Phase 1 Implementation Gameplan

### Objectives

- [x] Repository structure and development workflow (COMPLETED)
- [ ] Finalize `app.py` with full features
- [ ] Create systemd service file
- [ ] Test API locally and from external network
- [ ] Implement basic authentication (API key validation)
- [ ] Add structured logging and audit trails
- [ ] Document deployment procedures
- [ ] Create health check endpoint
- [ ] Establish monitoring/alerting foundation

### Detailed Implementation Tasks

#### Task 1.1: Complete `app.py` Enhancement

**Deliverable**: Updated `app.py` with:

**1.1.1 - Configuration Management**:
- [ ] Move ALLOWED_IDS to configurable source (start with comment-based config)
- [ ] Support `.env` file for API_KEY via `python-dotenv`
- [ ] Add configuration validation at startup
- [ ] Implement configuration reload on SIGHUP (optional Phase 1.5)

**1.1.2 - Error Handling**:
- [ ] Graceful handling of missing ALLOWED_IDS entries
- [ ] Permission errors when sending magic packets (log as WARNING)
- [ ] Network unreachability errors
- [ ] Return appropriate HTTP status codes (400, 403, 404, 500)

**1.1.3 - Logging Enhancements**:
- [ ] Add request IP address to logs
- [ ] Implement log rotation via RotatingFileHandler (already done in current code)
- [ ] Add structured JSON logging support (import JSONFormatter, configure)
- [ ] Track request duration and WOL send time

**1.1.4 - Input Validation**:
- [ ] Validate ID format (max 50 chars, alphanumeric)
- [ ] Validate API key format (min 20 chars, max 256 chars)
- [ ] Reject malformed/oversized inputs
- [ ] Rate limiting placeholder (log repeated requests from same IP)

**1.1.5 - Response Enhancements**:
- [ ] Add `timestamp` (ISO 8601 UTC) to all responses
- [ ] Include `mac` address in success response (if appropriate for security)
- [ ] Add unique request ID (X-Request-ID header)
- [ ] Return consistent error message structure

#### Task 1.2: Create Systemd Service File

**Deliverable**: `/etc/systemd/system/rustdesk-wol.service`

- [ ] Use gunicorn as WSGI server (see config above)
- [ ] Configure 2 workers (1 spare for safety)
- [ ] Set timeout to 30 seconds
- [ ] Add resource limits (256M memory, 50% CPU)
- [ ] Configure restart on failure (cooldown 10s)
- [ ] Use dedicated system user `rustdesk-wol`
- [ ] Load environment from `/opt/rustdesk-wol-proxy/.env`
- [ ] Add documentation link to service

**Installation Procedure**:
```bash
sudo cp rustdesk-wol.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rustdesk-wol
```

#### Task 1.3: Local Testing (Development)

**Test Environment**: Workstation with WSL2

- [ ] Start Flask dev server: `python app.py`
- [ ] Test `/wake` endpoint with valid parameters
- [ ] Test `/wake` with missing parameters (expect 400)
- [ ] Test `/wake` with invalid API key (expect 403)
- [ ] Test `/wake` with unknown ID (expect 404)
- [ ] Verify log output to `/var/log/rustdesk-wol-proxy.log` (create dev log path)
- [ ] Test concurrent requests (stress/load test): `ab -n 100 -c 10 "http://localhost:5001/wake?id=123&key=testkey"`

#### Task 1.4: Deployment to Production Server

**Steps**:
- [ ] SSH to 10.10.10.145
- [ ] Follow installation procedure (see Deployment Architecture section)
- [ ] Verify service is running: `systemctl status rustdesk-wol`
- [ ] Check port is listening: `sudo netstat -tlnp | grep 5001`
- [ ] Verify log file exists: `ls -lh /var/log/rustdesk-wol-proxy.log`

#### Task 1.5: Integration Testing (From External Network)

**Scenario**: Offsite client / different network

- [ ] Configure port forwarding or VPN access to 10.10.10.145:5001
- [ ] Test HTTP request from offsite: `curl "http://10.10.10.145:5001/wake?id=<TEST_ID>&key=<API_KEY>"`
- [ ] Verify response is valid JSON with 200 status
- [ ] Monitor log file: `tail -f /var/log/rustdesk-wol-proxy.log`
- [ ] Verify actual WOL packet is sent (observe target machine waking)

#### Task 1.6: Real-World WOL Test

**Test Case**: Full end-to-end WOL cycle

- [ ] Select target machine (must support WOL, have correct MAC in mapping)
- [ ] Manually power down target (or sleep)
- [ ] Call WOL API: `curl "http://10.10.10.145:5001/wake?id=<ID>&key=<KEY>"`
- [ ] Monitor target machine for power LED / wake indicators
- [ ] Confirm RustDesk service starts on target
- [ ] Verify broadcast packet seen in network capture (optional tcpdump verification)

#### Task 1.7: Documentation

- [ ] Document API key generation procedure
- [ ] Document ID ↔ MAC mapping collection process
- [ ] Create deployment guide (step-by-step)
- [ ] Create operational runbook (troubleshooting, monitoring)
- [ ] Document testing procedures
- [ ] Add comments to systemd service file

#### Task 1.8: Monitoring & Observability (Foundation)

- [ ] Create simple health check script that tests API
- [ ] Setup log file rotation (already configured in systemd)
- [ ] Create cron job for log archival (future)
- [ ] Document alerting thresholds (too many 403s → compromised key?)

### Success Criteria for Phase 1

- ✓ Flask API running as systemd service on 10.10.10.145:5001
- ✓ Authentication working (API key validation)
- ✓ WOL packets successfully sent to configured MAC addresses
- ✓ All requests logged with audit trail
- ✓ HTTP error responses correct (400, 403, 404, 500)
- ✓ External clients can invoke API (if exposed via proxy)
- ✓ Real hardware successfully woken via API call
- ✓ Service auto-restarts on failure
- ✓ Documentation complete for operations team

---

## Phase 2 Considerations (Client Integration)

*Phase 2 is OUT OF SCOPE for this architecture document but described for context.*

### Custom RustDesk Client Fork

**Modification Points**:
1. **Connection State Detection**: Hook into RustDesk connection logic to detect "peer offline" state
2. **Configuration UI**: Add settings panel for WOL API URL and API key
3. **WOL Invocation**: When offline detected → call `/wake` endpoint
4. **Retry Logic**: Wait N seconds for boot → attempt reconnection → repeat up to M times
5. **User Feedback**: Show "Waking machine…" notification during process

**Key Architecture Decisions**:
- Minimal fork diff from upstream RustDesk (reduce maintenance burden)
- Use existing Tokio async runtime for HTTP requests (no new dependencies)
- Store API key securely (avoid hardcoding)
- Make WOL optional feature (toggle in settings)

### Client-Side Configuration

**Settings to Distribute**:
```
wol_enabled: true
wol_api_url: "https://rustdesk-wol.internal.net/wake"  # or IP
wol_api_key: "wol_prod_xxxxx"
wol_retry_delay_seconds: 30
wol_retry_count: 3
```

**Distribution Methods**:
- Pre-built custom binaries
- Configuration file in RustDesk config directory
- In-app settings panel (encrypted storage)

### Security for Phase 2

- API key should NOT be visible in UI (bullets/stars)
- Key should be stored in OS keyring (Windows Credential Manager, macOS Keychain, Linux Secret Service)
- HTTPS required for external API calls
- Rate limiting enforced server-side

---

## Testing & Validation Strategy

### Unit Testing

**Framework**: pytest (to add to Phase 1.5)

**Test Cases**:
```python
# tests/test_app.py

def test_wake_success():
    """Valid ID and key should return 200 with success message"""
    response = client.get('/wake?id=123456789&key=secret-key')
    assert response.status_code == 200
    assert response.json['status'] == 'success'

def test_wake_missing_id():
    """Missing ID parameter should return 400"""
    response = client.get('/wake?key=secret-key')
    assert response.status_code == 400

def test_wake_invalid_key():
    """Invalid API key should return 403"""
    response = client.get('/wake?id=123456789&key=wrong-key')
    assert response.status_code == 403

def test_wake_unknown_id():
    """Unknown ID should return 404"""
    response = client.get('/wake?id=unknown&key=secret-key')
    assert response.status_code == 404

def test_wake_sends_packet(mocker):
    """WOL packet should be sent for valid request"""
    mock_send = mocker.patch('wakeonlan.send_magic_packet')
    response = client.get('/wake?id=123456789&key=secret-key')
    mock_send.assert_called_once_with('AA:BB:CC:DD:EE:FF', ip='10.10.10.255')
```

### Integration Testing

**Scope**: Full stack from HTTP request → magic packet

- [ ] Deploy to test server
- [ ] Fire request from local machine
- [ ] Verify packet appears in network capture on LAN
- [ ] Verify target machine receives broadcast

### Load Testing

**Tools**: Apache Bench (`ab`) or wrk

```bash
# 100 requests, 10 concurrent
ab -n 100 -c 10 "http://localhost:5001/wake?id=123456789&key=secret"

# Expected results:
# - All requests complete successfully (200 OK)
# - Response time < 100ms per request
# - No 50x errors
```

### Security Testing

- [ ] SQL injection attempts (not applicable, no SQL)
- [ ] API key brute force (test with rate limiting, future)
- [ ] Path traversal (test with ../ in parameters)
- [ ] Oversized payloads (test with 10MB parameter strings)
- [ ] Command injection (test with shell metacharacters in ID)

### User Acceptance Testing (UAT)

- [ ] IT manager confirms security posture acceptable
- [ ] Operations team runs deployment procedures successfully
- [ ] Real users test WOL from off-network location
- [ ] Verify network does not broadcast excessive magic packets

---

## Risk Analysis & Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|---|---|---|
| **Magic packet not received** | Medium | High | Verify network interface on server has proper MAC binding, test with tcpdump/Wireshark |
| **API key leaked in logs** | Low | Critical | Implement key masking (log first 8 chars only), use structured logging with field filtering |
| **Service crashes on boot** | Medium | High | Implement watchdog timer, systemd auto-restart (already configured) |
| **Race condition (simultaneous requests)** | Low | Low | gunicorn worker pool handles concurrency, WOL library is thread-safe |
| **Broadcast storms** | Low | Medium | Rate limiting per IP (future), alert on >100 requests/hour per ID |
| **Wrong MAC address in mapping** | Medium | Medium | Pre-validate all MAC addresses before deployment, require confirmation from network admin |

### Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|---|---|---|
| **API key compromise** | Medium | Critical | Rotate key quarterly, log all requests, implement rate limiting |
| **Unauthorized WOL (accidental)** | High | Low | Require explicit client action to wake, add confirmation dialog |
| **Log file fills disk** | Low | Medium | Automatic rotation configured (5MB × 3 files), monthly archival process |
| **Network config changes** | Low | High | Document broadcast address clearly, versioning for config changes |
| **Power budget exceeded** | Low | Medium | Stagger WOL requests (future), implement request queue |

### Security Risks

| Risk | Probability | Impact | Mitigation |
|------|---|---|---|
| **DoS via repeated WOL requests** | High | Medium | Rate limiting (Phase 2), IP blocking for >10 failed keys/min |
| **API key exposed in Git history** | High | Critical | Never commit API key; use `.env` files with `.gitignore` |
| **Information disclosure** | Medium | Medium | Reject unknown IDs silently (do not list valid IDs) |
| **Man-in-the-middle (HTTP)** | Medium | High | Use HTTPS when exposing externally (Nginx reverse proxy) |
| **Privilege escalation** | Low | Critical | Run service as non-root user (already configured), use systemd hardening (future) |

### Dependency Risks

| Dependency | Version | Risk | Mitigation |
|---|---|---|---|
| Flask | 3.0.3 | Security vulnerability | Monitor Flask security advisories, update quarterly |
| wakeonlan | 3.1.0 | Abandoned project? | Have backup implementation ready (pure Python socket code) |
| gunicorn | 23.0.0 | CVE exposure | Monitor releases, auto-patch via OS package management |
| Python | 3.8+ | EOL risk (3.8 EOL 2024) | Target Python 3.10+ for new deployments |

---

## Development Roadmap

### Phase 1: Backend API (Current - 4-6 Weeks)

**Milestone 1.1**: Core API Implementation
- [ ] Finalize `app.py` with all features
- [ ] Error handling complete
- [ ] Logging and audit trails working
- [ ] Input validation comprehensive
- **Deliverable**: Updated app.py file

**Milestone 1.2**: Systemd Integration
- [ ] Create and test systemd service file
- [ ] Document installation procedures
- [ ] Test on production server (10.10.10.145)
- **Deliverable**: `/etc/systemd/system/rustdesk-wol.service`

**Milestone 1.3**: Testing & Validation
- [ ] Unit tests written and passing
- [ ] Integration tests on production
- [ ] Real WOL scenario tested end-to-end
- [ ] Network capture verified
- **Deliverable**: Test reports, validation checklist

**Milestone 1.4**: Operations & Documentation
- [ ] Deployment runbook written
- [ ] Troubleshooting guide created
- [ ] Operations team trained
- [ ] Monitoring foundation in place
- **Deliverable**: Operational documentation

**Phase 1 Success Criteria**: API operational, tested, and monitored, ready for client integration

---

### Phase 2: Client Integration (6-12 Weeks)

**Milestone 2.1**: RustDesk Fork Setup
- [ ] Fork RustDesk repository
- [ ] Understand connection state machine
- [ ] Identify modification points
- **Deliverable**: Forked repo with modification plan

**Milestone 2.2**: WOL Detection & Invocation
- [ ] Hook into offline detection logic
- [ ] Implement WOL API call logic
- [ ] Add retry/backoff algorithm
- **Deliverable**: Core WOL functionality

**Milestone 2.3**: UI & Configuration
- [ ] Add settings panel for API URL and key
- [ ] Implement user notification ("Waking machine…")
- [ ] Store API key securely
- **Deliverable**: User-facing feature complete

**Milestone 2.4**: Testing & Binary Distribution
- [ ] Test forked client with Phase 1 API
- [ ] Build custom binaries (Windows, macOS, Linux)
- [ ] Distribute to pilot users
- **Deliverable**: Custom RustDesk builds available

**Phase 2 Success Criteria**: Offsite users can wake machines via custom client

---

### Phase 3: Hardening & Scaling (8-12 Weeks)

**Milestone 3.1**: Security Enhancements
- [ ] Implement rate limiting (server-side)
- [ ] Add HTTPS/TLS via reverse proxy
- [ ] Implement key rotation policy
- [ ] Add IP allowlisting
- **Deliverable**: Enhanced security posture

**Milestone 3.2**: Scalability & High Availability
- [ ] Move ID↔MAC mapping to database
- [ ] Implement caching layer (Redis)
- [ ] Load balance API across multiple instances
- [ ] Centralized logging (ELK/Splunk)
- **Deliverable**: HA infrastructure

**Milestone 3.3**: Monitoring & Observability
- [ ] Prometheus metrics exports
- [ ] Grafana dashboards
- [ ] Real-time alerting
- [ ] SLA definition & tracking
- **Deliverable**: Observability platform

**Milestone 3.4**: Documentation & Knowledge Transfer
- [ ] Create architecture wiki
- [ ] Record video tutorials
- [ ] Develop support runbook
- [ ] Train support team
- **Deliverable**: Comprehensive documentation

---

## Appendix: Configuration Examples

### .env File Template

```bash
# RustDesk WOL Proxy Configuration

# API Authentication
WOL_API_KEY=wol_prod_x9kJ2mL8nP3qR5sT7uV9wX1yZ4aB6cD8

# Network Configuration
BROADCAST_IP=10.10.10.255

# Logging
LOG_FILE=/var/log/rustdesk-wol-proxy.log
LOG_LEVEL=INFO

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_TESTING=False
```

### ID↔MAC Mapping Example

```python
ALLOWED_IDS = {
    "123456789": "AA:BB:CC:DD:EE:FF",      # Office Desktop
    "987654321": "11:22:33:44:55:66",      # Lab Server
    "456789123": "DE:AD:BE:EF:CA:FE",      # Conference Room PC
}
```

### Test Request Examples

**Valid Request**:
```bash
curl -X GET "http://10.10.10.145:5001/wake?id=123456789&key=wol_prod_x9kJ2mL8nP3qR5sT7uV9wX1yZ4aB6cD8"
```

**With HTTPS (Phase 2+)**:
```bash
curl -X GET "https://rustdesk-wol.internal.net/wake?id=123456789&key=wol_prod_x9kJ2mL8nP3qR5sT7uV9wX1yZ4aB6cD8"
```

**Using Python requests library**:
```python
import requests

api_url = "http://10.10.10.145:5001/wake"
params = {
    "id": "123456789",
    "key": "wol_prod_x9kJ2mL8nP3qR5sT7uV9wX1yZ4aB6cD8"
}

response = requests.get(api_url, params=params)
print(response.json())
```

---

## Glossary

| Term | Definition |
|------|-----------|
| **WOL** | Wake-on-LAN: Technology to remotely power on machines via network broadcast |
| **Magic Packet** | Special UDP packet (6 bytes of 0xFF + 16 repetitions of target MAC) that wakes WOL-capable machines |
| **Broadcast IP** | Network broadcast address (10.10.10.255 for 10.10.10.0/24 subnet) |
| **WSGI** | Web Server Gateway Interface; Python standard for web application servers |
| **gunicorn** | Python WSGI HTTP server for production deployments |
| **systemd** | Linux system service manager for process lifecycle |
| **API Key** | Shared secret for authentication (bearer token approach) |
| **RustDesk ID** | Global identifier for RustDesk client instance (36+ digit string) |
| **MAC Address** | Media Access Control address; unique hardware identifier on LAN (AA:BB:CC:DD:EE:FF format) |
| **Reverse Proxy** | Intermediate server (e.g., Nginx) that forwards requests to backend service |

---

## References & Further Reading

- [RustDesk GitHub Repository](https://github.com/rustdesk/rustdesk)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [gunicorn Documentation](https://gunicorn.org/)
- [Wake-on-LAN Wikipedia](https://en.wikipedia.org/wiki/Wake-on-LAN)
- [systemd.service Manual](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-10  
**Reviewed By**: Architecture Review Board  
**Status**: Ready for Implementation
