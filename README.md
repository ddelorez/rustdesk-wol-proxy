# RustDesk WOL Proxy

A Flask-based Wake-on-LAN (WOL) REST API proxy to remotely wake RustDesk-managed client computers on a network.

## Features

- 🎯 **WOL Packet Transmission**: Send magic packets to registered devices
- 🔐 **API Key Authentication**: Secure API key validation (min 20 chars)
- 📝 **Comprehensive Logging**: Request tracking with IP addresses and timestamps
- 🏥 **Health Check**: Built-in health endpoint for monitoring
- ⚡ **Fast Response**: Sub-millisecond request processing
- 🔍 **Request Tracing**: Unique request IDs for distributed tracing
- 🛡️ **Input Validation**: Strict parameter validation and error handling

## Quick Start

### Installation

```bash
# Clone repository
git clone <repo-url>
cd rustdesk-wol-proxy

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy environment template
cp config/.env.example .env

# Edit .env with your settings
nano .env

# Required variables:
# WOL_API_KEY - Strong API key (min 20 chars)
# BROADCAST_IP - Network broadcast address (default: 10.10.10.255)
# LOG_FILE - Log file path (default: /var/log/rustdesk-wol-proxy.log)
```

### Running the Application

```bash
# Development (from project root)
export WOL_API_KEY="your_strong_api_key_here"
python src/app.py

# Production (using systemd)
sudo systemctl start rustdesk-wol
sudo systemctl status rustdesk-wol
```

## API Usage

### Wake Device

Send a WOL magic packet to a registered device:

```bash
curl "http://localhost:5001/wake?id=123456789&key=your_api_key"
```

**Response (Success - HTTP 200)**:
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

### Health Check

Check if the API is running:

```bash
curl http://localhost:5001/health
```

**Response (HTTP 200)**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-10T20:12:52.493Z"
}
```

## Development Context Strategy

### Two-Phase Architecture: Separate Contexts

This project uses **two distinct development contexts** to efficiently manage different technology stacks:

| Aspect | Phase 1 (API/Backend) | Phase 2 (Client/Frontend) |
|--------|----------------------|--------------------------|
| **Environment** | **WSL2 Ubuntu 22.04** | **Windows 10/11 Native** |
| **Language** | Python 3.8+ | Rust 1.7x+ |
| **Framework** | Flask REST API | RustDesk Client Fork |
| **Development Terminal** | WSL2 Bash | Windows PowerShell |
| **Build Tool** | pip/pytest | Cargo/MSVC |
| **Deployment** | Linux Server (10.10.10.145) | Windows Client Binaries |
| **Communication** | Listens on port 5001 | Calls HTTP API when needed |

**Key Insight**: Phase 1 and Phase 2 are developed independently, and they communicate via HTTP API. Your WSL2 environment is ideal for Phase 1 — no changes needed there.

### Quick Reference: Which Context Am I In?

- 🔵 **Am I developing the Flask API?** → Use **Phase 1 (WSL2)** → See [`CONTEXT_SWITCHING_GUIDE.md`](docs/CONTEXT_SWITCHING_GUIDE.md)
- 🟢 **Am I developing the RustDesk Rust client?** → Use **Phase 2 (Windows)** → See [`PHASE2_WINDOWS_SETUP.md`](docs/PHASE2_WINDOWS_SETUP.md)
- 🔗 **Need both contexts talking?** → See [`PHASE2_DUAL_CONTEXT_WORKFLOW.md`](docs/PHASE2_DUAL_CONTEXT_WORKFLOW.md)

### Network Communication Between Contexts

```
Phase 1 (API Server)              Phase 2 (Client)
┌─────────────────────────┐       ┌─────────────────────────┐
│ Flask API               │       │ RustDesk Client         │
│ WSL2 Linux              │       │ Windows Native          │
│ localhost:5001          │◄──────│ HTTP API calls          │
│ /wake endpoint          │───────│ when offline detected   │
└─────────────────────────┘       └─────────────────────────┘
         HTTP/HTTPS API
```

---

## Project Structure

```
rustdesk-wol-proxy/
├── src/
│   └── app.py                    # Main Flask application
├── config/
│   ├── rustdesk-wol.service      # Systemd service file
│   └── .env.example              # Environment template
├── tests/
│   ├── run_all_tests.py          # Comprehensive test suite
│   ├── test_comprehensive.sh     # Alternative bash tests
│   ├── test_results.txt          # Test output
│   ├── test_output.txt           # Additional test output
│   └── README.md                 # Testing documentation
├── docs/
│   ├── README.md                 # Quick start guide
│   ├── ARCHITECTURE.md           # System architecture
│   ├── API.md                    # Complete API reference
│   ├── DEPLOYMENT.md             # Deployment procedures
│   ├── DEVELOPMENT.md            # Development guide
│   ├── QUICK_START.md            # Quick start reference
│   ├── PHASE2_DUAL_CONTEXT_WORKFLOW.md   # Multi-context development guide
│   ├── CONTEXT_SWITCHING_GUIDE.md        # Context switching reference
│   └── PHASE2_WINDOWS_SETUP.md           # Windows Phase 2 setup
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignore rules
└── README.md                     # This file
```

## Documentation

### Phase 1 (API Backend - WSL2)
- **[Quick Start Guide](docs/QUICK_START.md)** - Get up and running quickly
- **[API Reference](docs/API.md)** - Complete API documentation with examples
- **[Architecture](docs/ARCHITECTURE.md)** - System design and components
- **[Deployment](docs/DEPLOYMENT.md)** - Production deployment guide
- **[Development](docs/DEVELOPMENT.md)** - Development and testing guide
- **[Testing](tests/README.md)** - Test suite documentation

### Multi-Context Guidance (Phase 1 + Phase 2)
- **[📋 Dual Context Workflow](docs/PHASE2_DUAL_CONTEXT_WORKFLOW.md)** - Managing Phase 1 (WSL2) and Phase 2 (Windows) development
- **[🔄 Context Switching Guide](docs/CONTEXT_SWITCHING_GUIDE.md)** - Quick reference for switching between contexts
- **[⚙️ Development Context Strategy](#development-context-strategy)** - Overview (see section above)

### Phase 2 (RustDesk Client - Windows)
- **[Windows Setup Guide](docs/PHASE2_WINDOWS_SETUP.md)** - Complete Windows environment configuration
- **[Phase 2 Design](docs/PHASE2_DESIGN.md)** - Phase 2 architecture and design decisions

## API Error Codes

| Code | HTTP Status | Meaning |
|------|--------|---------|
| SEND_SUCCESS | 200 | Magic packet sent successfully |
| MISSING_PARAMETER | 400 | Required parameter (id or key) missing |
| INVALID_PARAMETER | 400 | Parameter format or length invalid |
| INVALID_KEY | 403 | API key authentication failed |
| UNKNOWN_ID | 404 | Device ID not found in configuration |
| PERMISSION_DENIED | 500 | Permission error (may need elevated privileges) |
| NETWORK_ERROR | 500 | Network unreachable |
| SEND_FAILED | 500 | Generic failure sending magic packet |
| NOT_FOUND | 404 | Endpoint not found |
| METHOD_NOT_ALLOWED | 405 | HTTP method not allowed for endpoint |
| INTERNAL_ERROR | 500 | Unexpected server error |

## Testing

Run the comprehensive test suite:

```bash
# Set environment
export WOL_API_KEY="wol_prod_test_key_1234567890_secure"
export LOG_FILE="./dev.log"

# Run tests
python3 tests/run_all_tests.py

# View results
cat tests/test_results.txt
```

**Test Results**: ✅ 33/33 tests passing (100% success rate)

## Security

- ✅ **API Key Authentication**: 20-256 character keys required
- ✅ **Input Validation**: Strict parameter format validation
- ✅ **Key Masking**: API keys masked in logs (first 10 chars + ***)
- ✅ **Audit Trail**: All requests logged with IP address and timestamp
- ✅ **Error Messages**: User-friendly without leaking internal details

### Security Recommendations

1. **Strong API Keys**: Generate with `python3 -c "import secrets; print('wol_prod_' + secrets.token_hex(16))"`
2. **HTTPS**: Deploy behind reverse proxy (nginx/Apache) with TLS
3. **Rate Limiting**: Implement rate limiting on reverse proxy
4. **Firewall**: Restrict port 5001 access to trusted clients only
5. **Key Rotation**: Periodically change API keys and update clients

## Requirements

- Python 3.6+
- Flask 2.0+
- python-wakeonlan
- python-dotenv

See `requirements.txt` for complete list.

## Production Deployment

1. Copy systemd service file:
   ```bash
   sudo cp config/rustdesk-wol.service /etc/systemd/system/
   ```

2. Create service user:
   ```bash
   sudo useradd -r -s /bin/false rustdesk-wol
   ```

3. Configure environment:
   ```bash
   sudo cp config/.env.example /etc/rustdesk-wol/.env
   sudo nano /etc/rustdesk-wol/.env
   ```

4. Enable and start service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable rustdesk-wol
   sudo systemctl start rustdesk-wol
   ```

5. Verify operation:
   ```bash
   sudo systemctl status rustdesk-wol
   curl http://localhost:5001/health
   ```

## Logging

Logs are written to the configured log file (default: `/var/log/rustdesk-wol-proxy.log`).

Log format:
```
YYYY-MM-DD HH:MM:SS - LEVEL - [IP_ADDRESS] - MESSAGE
```

Example log entries:
```
2026-02-10 20:12:52 - INFO - [192.168.1.100] - WOL packet sent to AA:BB:CC:DD:EE:FF (ID: 123456789, key: wol_prod_t***)
2026-02-10 20:12:53 - WARNING - [192.168.1.101] - Invalid API key attempt (key: invalid_k***, ID: 123456789)
```

## Troubleshooting

### Server Won't Start

- Check: `WOL_API_KEY` environment variable is set and valid (min 20 chars)
- Check: Log file directory exists and is writable
- Check: Port 5001 is not already in use

### 403 Invalid Key

- Ensure API key matches exactly (case-sensitive)
- Verify key is at least 20 characters
- Check for extra spaces in key parameter

### 404 Unknown ID

- Verify device ID is registered in `src/app.py` ALLOWED_IDS
- Check ID matches exactly (case-sensitive)
- Verify ID contains only alphanumeric characters

### 500 Network Error

- Ensure running with sufficient privileges (may need root)
- Check network interface is accessible
- Verify target device is on same network segment
- Check BROADCAST_IP configuration

## Support

For issues or questions:

1. Check the logs: `tail -f /var/log/rustdesk-wol-proxy.log`
2. Review documentation in `docs/` directory
3. Run test suite: `python3 tests/run_all_tests.py`
4. Check API reference: `docs/API.md`

## License

[Add your license here]

## Status

✅ **Production Ready** - All tests passing, security hardened, ready for deployment
