# RustDesk WOL Proxy - Quick Start Guide

## Overview

Get the RustDesk WOL Proxy API up and running in 10 minutes.

---

## Prerequisites

- Python 3.8+
- Linux/Unix environment (or WSL on Windows)
- Git
- curl (for testing)

---

## 5-Minute Development Setup

### 1. Get the Code
```bash
git clone https://github.com/ddelore/rustdesk-wol-proxy.git
cd rustdesk-wol-proxy
```

### 2. Setup Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure
```bash
cp .env.example .env
# Edit .env and set:
# WOL_API_KEY=wol_dev_testkey_1234567890
# BROADCAST_IP=127.0.0.1 (for testing)
```

### 4. Run
```bash
python app.py
```

### 5. Test
```bash
# In another terminal:
curl http://localhost:5001/health
```

**Expected**: `{"status":"healthy","version":"1.0.0",...}`

---

## 10-Minute Production Deployment

### On Target Server

```bash
# 1. Create directory and clone
sudo mkdir -p /opt/rustdesk-wol-proxy
cd /opt/rustdesk-wol-proxy
sudo git clone https://github.com/ddelore/rustdesk-wol-proxy.git .

# 2. Setup Python environment
sudo python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure (edit with your actual key)
sudo cp .env.example .env
sudo nano .env
# Set WOL_API_KEY, BROADCAST_IP, LOG_FILE

# 4. Setup system user
sudo useradd -r -s /bin/false rustdesk-wol 2>/dev/null || true
sudo chown -R rustdesk-wol:rustdesk-wol /opt/rustdesk-wol-proxy

# 5. Create log directory
sudo mkdir -p /var/log/rustdesk-wol
sudo touch /var/log/rustdesk-wol-proxy.log
sudo chown rustdesk-wol:rustdesk-wol /var/log/rustdesk-wol-proxy.log

# 6. Install service
sudo cp rustdesk-wol.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rustdesk-wol
sudo systemctl start rustdesk-wol

# 7. Verify
sudo systemctl status rustdesk-wol
curl http://localhost:5001/health
```

---

## Testing

### Run All Tests
```bash
python run_all_tests.py
```

**Expected**: All 33 tests pass ✓

### Manual API Testing

```bash
# Health check (no auth required)
curl http://localhost:5001/health

# WOL request (requires valid API key and device ID)
curl "http://localhost:5001/wake?id=123456789&key=wol_dev_testkey_1234567890"

# Test with invalid key
curl "http://localhost:5001/wake?key=invalid"
```

---

## Common Issues

### API Key Too Short
```
Error: WOL_API_KEY is too short. Minimum 20 characters required
```
**Fix**: Generate longer key:
```bash
python3 -c "import secrets; print('wol_dev_' + secrets.token_hex(16))"
```

### Port Already in Use
```
Address already in use
```
**Fix**: 
```bash
sudo lsof -i :5001
sudo kill -9 <PID>
```

### Log File Permission Error
```
PermissionError: Permission denied: '/var/log/rustdesk-wol-proxy.log'
```
**Fix**:
```bash
sudo chmod 644 /var/log/rustdesk-wol-proxy.log
sudo chown rustdesk-wol:rustdesk-wol /var/log/rustdesk-wol-proxy.log
```

### WOL Not Working
- Check MAC address is registered in `app.py` ALLOWED_IDS
- Verify BROADCAST_IP matches your network (e.g., 10.10.10.255)
- Ensure target device has WOL enabled in BIOS
- Check service is running: `systemctl status rustdesk-wol`

---

## API Endpoints

### Health Check
```bash
GET /health
# No authentication required
# Response: {"status":"healthy","version":"1.0.0","timestamp":"..."}
```

### Wake-on-LAN
```bash
GET /wake?id=<device_id>&key=<api_key>
# Parameters:
#   id: Device ID (max 50 chars, alphanumeric)
#   key: API key (min 20 chars)
# Response (200): {"status":"success","id":"...","mac":"..."}
# Response (403): {"status":"error","code":"INVALID_KEY"}
# Response (404): {"status":"error","code":"UNKNOWN_ID"}
```

---

## Configuration

Create `.env` file with:

```bash
# REQUIRED: Authentication key
WOL_API_KEY=wol_prod_<strong_random_key>

# OPTIONAL: Network broadcast address (default: 10.10.10.255)
BROADCAST_IP=10.10.10.255

# OPTIONAL: Log file path (default: /var/log/rustdesk-wol-proxy.log)
LOG_FILE=/var/log/rustdesk-wol-proxy.log
```

### Add Devices

Edit `app.py` around line 73:
```python
ALLOWED_IDS = {
    "123456789": "AA:BB:CC:DD:EE:FF",   # RustDesk ID → MAC
    "987654321": "11:22:33:44:55:66",
}
```

Then restart: `sudo systemctl restart rustdesk-wol`

---

## Monitoring

```bash
# Service status
systemctl status rustdesk-wol

# View logs
tail -f /var/log/rustdesk-wol-proxy.log

# Search for errors
grep ERROR /var/log/rustdesk-wol-proxy.log

# Check port listening
ss -tlnp | grep 5001
```

---

## Next Steps

- **API Details**: See [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Development**: See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- **Deployment**: See [DEPLOYMENT_PROCEDURES.md](DEPLOYMENT_PROCEDURES.md)
- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Support

**Something not working?**

1. Check logs: `tail -f /var/log/rustdesk-wol-proxy.log`
2. Verify service: `systemctl status rustdesk-wol`
3. Test health: `curl http://localhost:5001/health`
4. See DEPLOYMENT_PROCEDURES.md Troubleshooting section

---

**Version**: 1.0.0  
**Last Updated**: 2026-02-10
