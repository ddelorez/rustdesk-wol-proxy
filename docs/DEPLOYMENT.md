# RustDesk WOL Proxy - Deployment Procedures

## Overview

This document provides step-by-step procedures for deploying the RustDesk WOL Proxy to production servers. It includes pre-deployment checklist, detailed deployment steps, verification procedures, and troubleshooting guidance.

**Version**: 1.0.0  
**Target Environment**: Linux servers (Ubuntu 20.04+, RHEL 8+, Debian 10+)  
**Deployment Method**: Systemd service  
**Default Port**: 5001

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment Steps](#deployment-steps)
3. [Verification Procedures](#verification-procedures)
4. [Post-Deployment Checks](#post-deployment-checks)
5. [Rollback Procedures](#rollback-procedures)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance](#maintenance)

---

## Pre-Deployment Checklist

Before beginning deployment, verify the following:

### Code Quality

- [ ] All unit tests pass: `python run_all_tests.py`
- [ ] Code style validated: `pylint app.py` (if installed)
- [ ] No debug code in production branch
- [ ] All dependencies documented in `requirements.txt`
- [ ] Version in code matches release version

### Configuration

- [ ] `.env.example` exists with all required variables
- [ ] Production API key generated (min 20 chars, strong entropy)
- [ ] Production broadcast IP verified for target network
- [ ] Log file destination writable by service user
- [ ] Device ID to MAC mappings prepared

### Infrastructure

- [ ] Target server reachable and accessible
- [ ] Port 5001 not in use on target server
- [ ] Sufficient disk space: `/opt/` (min 500MB) and `/var/log/` (min 1GB)
- [ ] Network connectivity from RustDesk server verified
- [ ] Firewall rules allow port 5001 from RustDesk server IP

### Documentation

- [ ] API_DOCUMENTATION.md reviewed and current
- [ ] ARCHITECTURE.md reviewed for any changes
- [ ] Deployment plan documented
- [ ] Change log updated
- [ ] Team notified of maintenance window

### Backup

- [ ] Current production configuration backed up (if upgrading)
- [ ] Database backups current (if applicable)
- [ ] Rollback plan documented

---

## Deployment Steps

### Step 1: Create Application Directory

**Objective**: Set up the directory structure for the application

**Commands**:
```bash
# Create application directory
sudo mkdir -p /opt/rustdesk-wol-proxy

# Verify creation
ls -ld /opt/rustdesk-wol-proxy
```

**Verification**:
```bash
# Should show:
# drwxr-xr-x ... /opt/rustdesk-wol-proxy
```

**Troubleshooting**:
- If permission denied: Use `sudo` or ensure user has elevated privileges
- If already exists: Safe to continue; permissions will be set in Step 6

### Step 2: Clone Repository

**Objective**: Get the latest application code

**Options**:

#### 2A: Fresh Clone (New Deployment)

```bash
# Navigate to parent directory
cd /opt

# Clone repository
sudo git clone https://github.com/ddelore/rustdesk-wol-proxy.git rustdesk-wol-proxy

# Verify clone
ls -la /opt/rustdesk-wol-proxy/
```

**Expected files**:
```
app.py
requirements.txt
.env.example
rustdesk-wol.service
README.md
ARCHITECTURE.md
API_DOCUMENTATION.md
DEVELOPER_GUIDE.md
DEPLOYMENT_PROCEDURES.md
```

#### 2B: Update Existing (Upgrade Deployment)

```bash
# Navigate to application directory
cd /opt/rustdesk-wol-proxy

# Stop service first
sudo systemctl stop rustdesk-wol.service

# Pull latest changes
sudo git pull origin main

# Verify changes
git log --oneline -1

# Update requirements if needed
sudo source venv/bin/activate && pip install -r requirements.txt
```

**Verification**:
```bash
# Check repository status
git status

# Should show: On branch main, nothing to commit
```

### Step 3: Create Python Virtual Environment

**Objective**: Isolate application dependencies from system Python

**Commands**:
```bash
# Navigate to application directory
cd /opt/rustdesk-wol-proxy

# Create virtual environment
sudo python3 -m venv venv

# Verify creation
ls -la venv/

# Activate virtual environment
source venv/bin/activate

# Verify activation (prompt should show (venv))
which python

# Should show: /opt/rustdesk-wol-proxy/venv/bin/python
```

**Troubleshooting**:
- `python3: No module named venv` → Install: `sudo apt-get install python3-venv`
- Permission denied → Use `sudo` or ensure directory ownership

### Step 4: Install Dependencies

**Objective**: Install required Python packages

**Commands**:
```bash
# Ensure virtual environment activated
source /opt/rustdesk-wol-proxy/venv/bin/activate

# Upgrade pip (recommended)
pip install --upgrade pip setuptools wheel

# Install application requirements
pip install -r requirements.txt

# Verify installation
pip list
```

**Expected packages**:
```
Flask==2.3.x or higher
wakeonlan==0.2.2 or higher
python-dotenv==0.x.x
```

**Verification**:
```bash
# Test imports
python3 -c "import flask, wakeonlan, dotenv"

# Should produce no error
```

**Troubleshooting**:
- `No module named 'wheel'` → Already installed via --upgrade
- `Requirement already satisfied` → Safe to continue
- Missing package → Check requirements.txt integrity

### Step 5: Configure Environment File

**Objective**: Set production configuration variables

**Commands**:
```bash
# Copy example configuration
sudo cp /opt/rustdesk-wol-proxy/.env.example /opt/rustdesk-wol-proxy/.env

# Edit configuration (use your preferred editor)
sudo nano /opt/rustdesk-wol-proxy/.env

# Or: sudo vi /opt/rustdesk-wol-proxy/.env
```

**Configuration Values**:

#### .env File Content

```bash
# API Authentication Key (REQUIRED)
# Generate: python3 -c "import secrets; print('wol_prod_' + secrets.token_hex(16))"
WOL_API_KEY=wol_prod_<your_strong_random_key>

# Network Broadcast Address (OPTIONAL)
# Default: 10.10.10.255
# For your network: <network>.255 (e.g., 192.168.1.255)
BROADCAST_IP=10.10.10.255

# Log File Path (OPTIONAL)
# Default: /var/log/rustdesk-wol-proxy.log
LOG_FILE=/var/log/rustdesk-wol-proxy.log
```

**Generate Strong API Key**:
```bash
# Option 1: Using Python
python3 -c "import secrets; print('wol_prod_' + secrets.token_hex(16))"

# Option 2: Using openssl
openssl rand -hex 16

# Option 3: Using dd
dd if=/dev/urandom bs=1 count=32 2>/dev/null | base64
```

**Example Generated Keys**:
```
wol_prod_a1b2c3d4e5f6789012345678901abc12
wol_prod_f47ac10b58cc4372a5670e02b2c3d479
```

**Verification**:
```bash
# Check file was created
ls -la /opt/rustdesk-wol-proxy/.env

# Verify format
cat /opt/rustdesk-wol-proxy/.env

# Should show your configuration
```

**Troubleshooting**:
- No .env.example found → Clone repository failed; retry Step 2
- Permission denied → Use `sudo` or `sudo -i` for editor
- Key too short → Regenerate with stronger requirement

### Step 6: Create Log Directory and File

**Objective**: Ensure log file can be written by the service

**Commands**:
```bash
# Create log directory
sudo mkdir -p /var/log/rustdesk-wol

# Create log file (empty)
sudo touch /var/log/rustdesk-wol-proxy.log

# Verify creation
ls -la /var/log/rustdesk-wol*

# Should show:
# drwxr-xr-x ... /var/log/rustdesk-wol/
# -rw-r--r-- ... /var/log/rustdesk-wol-proxy.log
```

**Troubleshooting**:
- Permission denied → Already handled by `sudo`
- File system full → Check disk space: `df -h /var/log/`

### Step 7: Create Dedicated System User

**Objective**: Run service with minimal privileges

**Commands**:
```bash
# Check if user already exists
id rustdesk-wol

# Create user if not exists (use this only if user doesn't exist)
sudo useradd -r -s /bin/false rustdesk-wol

# If user already exists, skip this
# User should have system user properties:
# - uid < 1000 (system user)
# - shell: /bin/false (no login)
# - no home directory

# Verify user creation
id rustdesk-wol

# Should show:
# uid=XXX(...) gid=YYY(...) groups=ZZZ(...)
```

**Set Directory Ownership**:
```bash
# Set ownership of application directory
sudo chown -R rustdesk-wol:rustdesk-wol /opt/rustdesk-wol-proxy

# Set permissions (rwxr-xr-x)
sudo chmod -R 755 /opt/rustdesk-wol-proxy

# Set ownership of log file
sudo chown rustdesk-wol:rustdesk-wol /var/log/rustdesk-wol-proxy.log

# Set permissions (rw-r--r--)
sudo chmod 644 /var/log/rustdesk-wol-proxy.log
```

**Verification**:
```bash
# Check application directory ownership
ls -lad /opt/rustdesk-wol-proxy

# Should show: drwxr-xr-x rustdesk-wol rustdesk-wol

# Check log file ownership
ls -la /var/log/rustdesk-wol-proxy.log

# Should show: -rw-r--r-- rustdesk-wol rustdesk-wol
```

**Troubleshooting**:
- User already exists with different shell → Update: `sudo usermod -s /bin/false rustdesk-wol`
- Permission denied → Use `sudo` or login as root
- User not created → Check system logs: `sudo journalctl -xe`

### Step 8: Install Systemd Service File

**Objective**: Set up automatic service startup and management

**Commands**:
```bash
# Copy service file to systemd directory
sudo cp /opt/rustdesk-wol-proxy/rustdesk-wol.service /etc/systemd/system/

# Verify copy
ls -la /etc/systemd/system/rustdesk-wol.service

# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Verify service is recognized
systemctl list-unit-files | grep rustdesk-wol

# Should show: rustdesk-wol.service    enabled
```

**Service File Content** (for reference):
```ini
[Unit]
Description=RustDesk WOL Proxy API Service
Documentation=https://github.com/ddelore/rustdesk-wol-proxy
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=rustdesk-wol
Group=rustdesk-wol
WorkingDirectory=/opt/rustdesk-wol-proxy
EnvironmentFile=/opt/rustdesk-wol-proxy/.env
ExecStart=/opt/rustdesk-wol-proxy/venv/bin/python app.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Verification**:
```bash
# Display service file
systemctl cat rustdesk-wol.service

# Check syntax
sudo systemd-analyze verify rustdesk-wol.service

# Should show: OK
```

**Troubleshooting**:
- Service file not found → Copy failed; try again with `sudo`
- `[Service]` section missing → File corrupted; recopy from repository
- Syntax error → Check file with: `sudo systemctl status rustdesk-wol.service`

### Step 9: Enable and Start Service

**Objective**: Autostart service and run it immediately

**Commands**:
```bash
# Enable service (autostart on boot)
sudo systemctl enable rustdesk-wol.service

# Verify enabled
systemctl is-enabled rustdesk-wol.service

# Should output: enabled

# Start service
sudo systemctl start rustdesk-wol.service

# Check status
sudo systemctl status rustdesk-wol.service

# Should show: Active: active (running)
```

**Typical Status Output**:
```
● rustdesk-wol.service - RustDesk WOL Proxy API Service
     Loaded: loaded (/etc/systemd/system/rustdesk-wol.service; enabled)
     Active: active (running) since Mon 2026-02-10 14:30:45 UTC; 2min ago
     Process: PID=12345 ExecStart=/opt/rustdesk-wol-proxy/venv/bin/python app.py
    Main PID: 12346 (python)
      Tasks: 1 (limit: 512)
     Memory: 45.2M
     CGroup: /system.slice/rustdesk-wol.service
             └─12346 /opt/rustdesk-wol-proxy/venv/bin/python app.py
```

**Troubleshooting**:
- `Permission denied` → Use `sudo` or login as root
- `Failed to start` → Check logs: `sudo journalctl -u rustdesk-wol -n 50`
- `active (dead)` → See Troubleshooting section below

---

## Verification Procedures

### Immediate Verification (After Starting Service)

#### 1. Service Status Check

```bash
# Check service is running
systemctl is-active rustdesk-wol

# Should output: active

# If not active:
sudo journalctl -u rustdesk-wol -n 20 --no-pager
```

#### 2. Port Listening Check

```bash
# Check port 5001 is listening
ss -tlnp | grep 5001

# Or:
netstat -tlnp | grep 5001

# Should show something like:
# LISTEN  0  128  0.0.0.0:5001  0.0.0.0:*  (process_id)/python
```

**If port not listening**:
```bash
# Check for port conflicts
sudo lsof -i :5001

# Check service logs
sudo journalctl -u rustdesk-wol -n 50
```

#### 3. Health Endpoint Check

```bash
# Test health endpoint locally
curl http://127.0.0.1:5001/health

# Expected response:
# {"status":"healthy","version":"1.0.0","timestamp":"2026-02-10T...Z"}
```

#### 4. Log File Check

```bash
# Verify log file was created
ls -lah /var/log/rustdesk-wol-proxy.log

# Check for startup messages
tail -n 20 /var/log/rustdesk-wol-proxy.log

# Should contain startup logs like:
# 2026-02-10 14:30:45 - INFO - - RustDesk WOL Proxy starting
```

### WOL Functionality Verification

#### Test 1: Health Endpoint (No Auth Required)

```bash
curl -i http://localhost:5001/health

# Expected response (HTTP 200):
# {"status":"healthy","version":"1.0.0","timestamp":"2026-02-10T...Z"}
```

#### Test 2: Valid WOL Request

```bash
# Requires: valid API key and registered device ID
API_KEY="wol_prod_<your_actual_key>"
DEVICE_ID="123456789"

curl -i "http://localhost:5001/wake?id=$DEVICE_ID&key=$API_KEY"

# Expected response (HTTP 200):
# {"status":"success","code":"SEND_SUCCESS","message":"Wake-on-LAN packet..."}
```

#### Test 3: Invalid API Key

```bash
curl -i "http://localhost:5001/wake?id=123456789&key=invalidkey"

# Expected response (HTTP 403):
# {"status":"error","code":"INVALID_KEY","message":"Invalid API key"...}
```

#### Test 4: Unknown Device ID

```bash
API_KEY="wol_prod_<your_actual_key>"

curl -i "http://localhost:5001/wake?id=wrongid&key=$API_KEY"

# Expected response (HTTP 404):
# {"status":"error","code":"UNKNOWN_ID","message":"No MAC address..."...}
```

#### Test 5: Missing Parameters

```bash
# Missing device ID
curl -i "http://localhost:5001/wake?key=wol_prod_key"

# Expected response (HTTP 400):
# {"status":"error","code":"MISSING_PARAMETER","message":"Missing id parameter"...}

# Missing API key
curl -i "http://localhost:5001/wake?id=123456789"

# Expected response (HTTP 400):
# {"status":"error","code":"MISSING_PARAMETER","message":"Missing key parameter"...}
```

### Request Header Verification

```bash
# Check response headers
curl -i http://localhost:5001/health

# Should include:
# X-Request-ID: f47ac10b-58cc-4372-a567-0e02b2c3d479
# X-Request-Duration-Ms: 5
```

### Timestamp Format Verification

```bash
# Get health response
curl http://localhost:5001/health | jq .

# Verify timestamp format:
# - ISO 8601 format: YYYY-MM-DDTHH:MM:SS.sssZ
# - Example: 2026-02-10T20:12:52.493Z
# - Must end with 'Z' (UTC indicator)
```

---

## Post-Deployment Checks

### Day 1 Verification

- [ ] Service running: `systemctl is-active rustdesk-wol`
- [ ] Service enabled: `systemctl is-enabled rustdesk-wol`
- [ ] Port listening: `ss -tlnp | grep 5001`
- [ ] Health endpoint: `curl http://localhost:5001/health`
- [ ] Log file present: `ls -lh /var/log/rustdesk-wol-proxy.log`
- [ ] No errors in logs: `grep ERROR /var/log/rustdesk-wol-proxy.log`
- [ ] Requests from RustDesk server successful: `curl http://localhost:5001/health` (from RustDesk server IP)

### Week 1 Verification

- [ ] Service still running after reboot (if system restarted)
- [ ] No permission errors in logs
- [ ] No network errors in logs
- [ ] API key working for authenticated requests
- [ ] All registered devices WOL-able
- [ ] Response times reasonable (<50ms for health check)
- [ ] No failed authentication attempts logged

### Ongoing Monitoring

```bash
# Monitor service health
watch -n 5 'systemctl status rustdesk-wol | head -10'

# Monitor logs in real-time
tail -f /var/log/rustdesk-wol-proxy.log

# Check for repeated errors
grep "ERROR" /var/log/rustdesk-wol-proxy.log | tail -20

# Monitor disk usage
df -h /var/log

# Check process memory usage
ps aux | grep rustdesk-wol
```

---

## Rollback Procedures

### Scenario: Deployment Failed During Installation

**If service failed to start**:

```bash
# 1. Stop any running instance
sudo systemctl stop rustdesk-wol.service

# 2. Check error logs
sudo journalctl -u rustdesk-wol -n 50 --no-pager

# 3. Fix the issue (see Troubleshooting)

# 4. Restart service
sudo systemctl start rustdesk-wol.service

# 5. Verify
sudo systemctl status rustdesk-wol.service
```

### Scenario: Upgrade Failed

**If new version breaks existing deployment**:

```bash
# 1. Stop service
sudo systemctl stop rustdesk-wol.service

# 2. Restore previous code
cd /opt/rustdesk-wol-proxy
sudo git checkout HEAD~1  # Go back one commit

# Or restore from backup if available:
# sudo cp /backup/rustdesk-wol-proxy/* /opt/rustdesk-wol-proxy/

# 3. Reinstall dependencies if needed
source venv/bin/activate
pip install -r requirements.txt

# 4. Restart service
sudo systemctl start rustdesk-wol.service

# 5. Verify
sudo systemctl status rustdesk-wol.service
```

### Scenario: Complete Service Removal

**To completely remove the service**:

```bash
# 1. Stop service
sudo systemctl stop rustdesk-wol.service

# 2. Disable service
sudo systemctl disable rustdesk-wol.service

# 3. Remove service file
sudo rm /etc/systemd/system/rustdesk-wol.service

# 4. Reload systemd
sudo systemctl daemon-reload

# 5. Optional: Remove application directory
sudo rm -rf /opt/rustdesk-wol-proxy

# 6. Optional: Remove log files
sudo rm -rf /var/log/rustdesk-wol*

# 7. Optional: Remove user
sudo userdel rustdesk-wol
```

---

## Troubleshooting

### Service Won't Start

**Symptoms**: `systemctl status` shows "failed" or "dead"

**Diagnosis**:
```bash
# Check detailed error
sudo journalctl -u rustdesk-wol -n 50

# Check Python errors
sudo -u rustdesk-wol /opt/rustdesk-wol-proxy/venv/bin/python app.py
```

**Common Causes**:

#### 1. Missing WOL_API_KEY
```
FATAL: WOL_API_KEY environment variable not set
```

**Fix**:
```bash
sudo nano /opt/rustdesk-wol-proxy/.env
# Add: WOL_API_KEY=wol_prod_<your_key>

sudo systemctl restart rustdesk-wol
```

#### 2. API Key Too Short
```
FATAL: WOL_API_KEY is too short. Minimum 20 characters required
```

**Fix**: Generate new key with at least 20 characters
```bash
python3 -c "import secrets; print('wol_prod_' + secrets.token_hex(16))"

sudo nano /opt/rustdesk-wol-proxy/.env
# Update WOL_API_KEY value

sudo systemctl restart rustdesk-wol
```

#### 3. Log Directory Permission Error
```
PermissionError: [Errno 13] Permission denied: '/var/log/rustdesk-wol-proxy.log'
```

**Fix**:
```bash
sudo mkdir -p /var/log/rustdesk-wol
sudo touch /var/log/rustdesk-wol-proxy.log
sudo chown rustdesk-wol:rustdesk-wol /var/log/rustdesk-wol-proxy.log

sudo systemctl restart rustdesk-wol
```

#### 4. Port Already in Use
```
Address already in use
```

**Fix**:
```bash
# Find process using port 5001
sudo lsof -i :5001

# Kill the process
sudo kill -9 <PID>

# Or change port in systemd service
sudo nano /etc/systemd/system/rustdesk-wol.service
# Modify ExecStart to use different port

sudo systemctl daemon-reload
sudo systemctl start rustdesk-wol
```

### Health Endpoint Returns Error

**Symptoms**: `curl http://localhost:5001/health` returns error

**Diagnosis**:
```bash
# Check service running
systemctl is-active rustdesk-wol

# Check port listening
ss -tlnp | grep 5001

# Check recent logs
tail -n 20 /var/log/rustdesk-wol-proxy.log
```

**Common Causes**:

#### 1. Service Not Running
```bash
sudo systemctl start rustdesk-wol
```

#### 2. Port Not Listening
```bash
# Check service logs for startup errors
sudo journalctl -u rustdesk-wol -n 20
```

#### 3. Network Connectivity Issue
```bash
# Try localhost first
curl -v http://127.0.0.1:5001/health

# Try with explicit port
curl -v http://localhost:5001/health
```

### WOL Packet Not Sending

**Symptoms**: Valid WOL request returns success but device doesn't wake

**Diagnosis**:
```bash
# Check logs for "WOL packet sent"
tail -f /var/log/rustdesk-wol-proxy.log | grep "WOL packet"

# Check for permission errors
tail -f /var/log/rustdesk-wol-proxy.log | grep "Permission"

# Check for network errors
tail -f /var/log/rustdesk-wol-proxy.log | grep "Network"
```

**Common Causes**:

#### 1. Wrong Broadcast IP
```bash
# Check configured IP
grep BROADCAST_IP /opt/rustdesk-wol-proxy/.env

# Verify it's correct for your network
# Example: 192.168.1.255 for 192.168.1.0/24 network

sudo nano /opt/rustdesk-wol-proxy/.env
# Update BROADCAST_IP if needed

sudo systemctl restart rustdesk-wol
```

#### 2. Wrong MAC Address
```bash
# Verify MAC in app.py
grep -A 5 "ALLOWED_IDS" /opt/rustdesk-wol-proxy/app.py

# Get device MAC address
# On linux: ip link show
# On macOS: ifconfig
# On Windows: ipconfig /all

# Edit app.py and correct MAC
sudo nano /opt/rustdesk-wol-proxy/app.py

sudo systemctl restart rustdesk-wol
```

#### 3. Insufficient Privileges
```
Permission denied while sending magic packet
```

**Fix**:
```bash
# Service usually needs elevated privileges
# Verify service user
grep ^User /etc/systemd/system/rustdesk-wol.service

# Option 1: Run as root
sudo nano /etc/systemd/system/rustdesk-wol.service
# Change: User=root

sudo systemctl daemon-reload
sudo systemctl restart rustdesk-wol

# Option 2: Give sudo capability to rustdesk-wol user
sudo visudo
# Add line: rustdesk-wol ALL=(ALL) NOPASSWD: /usr/bin/python3
```

#### 4. Network Not Reachable
```
Network is unreachable
```

**Fix**:
```bash
# Verify network interface accessible
ip link show

# Test broadcast connectivity
ping 10.10.10.255 (or your broadcast IP)

# Check network configuration
ip addr show
```

### Authentication Failures

**Symptoms**: All requests return 403 Invalid API Key

**Diagnosis**:
```bash
# Check configured API key
grep WOL_API_KEY /opt/rustdesk-wol-proxy/.env

# Check logs
tail -f /var/log/rustdesk-wol-proxy.log | grep "Invalid API key"
```

**Common Causes**:

#### 1. API Key Mismatch
```bash
# Get configured key
CONFIG_KEY=$(grep WOL_API_KEY /opt/rustdesk-wol-proxy/.env | cut -d'=' -f2)

# Test with correct key
curl "http://localhost:5001/wake?id=123456789&key=$CONFIG_KEY"
```

#### 2. Typo in Request
```bash
# Verify key in request is exact match
# Check for extra spaces
# Case-sensitive comparison

curl "http://localhost:5001/wake?id=123456789&key=wol_prod_yourkeyhere"
```

### Log File Issues

**Symptoms**: No logs or error writing logs

**Diagnosis**:
```bash
# Check log file
ls -la /var/log/rustdesk-wol-proxy.log

# Check permissions
stat /var/log/rustdesk-wol-proxy.log

# Check file size
du -h /var/log/rustdesk-wol-proxy.log
```

**Common Causes**:

#### 1. File Not Writable
```bash
sudo chmod 644 /var/log/rustdesk-wol-proxy.log
sudo chown rustdesk-wol:rustdesk-wol /var/log/rustdesk-wol-proxy.log

sudo systemctl restart rustdesk-wol
```

#### 2. Disk Full
```bash
# Check disk space
df -h /var/log

# If full, archive old logs
sudo gzip /var/log/rustdesk-wol-proxy.log.1
sudo rm -f /var/log/rustdesk-wol-proxy.log.2+

# Or remove old logs
sudo journalctl --vacuum=500M
```

#### 3. Log Rotation Issue
```bash
# Check logrotate configuration
cat /etc/logrotate.d/*wol* 2>/dev/null || echo "No log rotation config"

# Create one if needed
sudo tee /etc/logrotate.d/rustdesk-wol <<EOF
/var/log/rustdesk-wol-proxy.log {
    daily
    rotate 7
    missingok
    notifempty
    compress
    delaycompress
    postrotate
        systemctl reload-or-restart rustdesk-wol.service > /dev/null 2>&1 || true
    endscript
}
EOF
```

---

## Maintenance

### Regular Maintenance Tasks

#### Daily
```bash
# Check service is running
systemctl is-active rustdesk-wol

# Check for errors
grep ERROR /var/log/rustdesk-wol-proxy.log | tail -5
```

#### Weekly
```bash
# Check disk usage
du -h /var/log/rustdesk-wol-proxy.log

# Review failed authentications
grep "Invalid API key" /var/log/rustdesk-wol-proxy.log | wc -l

# Check service uptime
systemctl status rustdesk-wol | grep "Active:"
```

#### Monthly
```bash
# Update package dependencies
cd /opt/rustdesk-wol-proxy
source venv/bin/activate
pip list --outdated
pip install --upgrade -r requirements.txt

# Check for application updates
git fetch origin
git log --oneline -1 origin/main
# If newer version available, plan upgrade

# Review and archive logs
sudo gzip /var/log/rustdesk-wol-proxy.log
sudo touch /var/log/rustdesk-wol-proxy.log
sudo chown rustdesk-wol:rustdesk-wol /var/log/rustdesk-wol-proxy.log
```

### Backup Procedures

```bash
# Backup current configuration
sudo cp /opt/rustdesk-wol-proxy/.env /backup/rustdesk-wol.env.$(date +%Y%m%d)

# Backup systemd service
sudo cp /etc/systemd/system/rustdesk-wol.service /backup/rustdesk-wol.service.$(date +%Y%m%d)

# Backup entire application
sudo tar -czf /backup/rustdesk-wol-proxy.$(date +%Y%m%d).tar.gz /opt/rustdesk-wol-proxy
```

### Service Restart Procedures

**Safe restart** (with verification):
```bash
# Check current status
sudo systemctl status rustdesk-wol

# Stop service
sudo systemctl stop rustdesk-wol

# Wait 5 seconds
sleep 5

# Start service
sudo systemctl start rustdesk-wol

# Verify it started
sleep 2
sudo systemctl status rustdesk-wol

# Test health
curl http://localhost:5001/health
```

**Immediate restart** (for emergency):
```bash
sudo systemctl restart rustdesk-wol

# Usually completes within 1 second
```

---

## Support & Resources

### Useful Commands Quick Reference

```bash
# Service management
sudo systemctl status rustdesk-wol
sudo systemctl start rustdesk-wol
sudo systemctl stop rustdesk-wol
sudo systemctl restart rustdesk-wol
sudo systemctl enable rustdesk-wol
sudo systemctl disable rustdesk-wol

# Logging
tail -f /var/log/rustdesk-wol-proxy.log
sudo journalctl -u rustdesk-wol -n 50
grep "ERROR" /var/log/rustdesk-wol-proxy.log

# Network
curl http://localhost:5001/health
ss -tlnp | grep 5001
sudo lsof -i :5001

# System
df -h /var/log
ps aux | grep rustdesk-wol
```

### Getting Help

1. Check logs first: `tail -f /var/log/rustdesk-wol-proxy.log`
2. Review this document's Troubleshooting section
3. Check API_DOCUMENTATION.md for API reference
4. Review DEVELOPER_GUIDE.md for code details
5. Check systemd journal: `sudo journalctl -u rustdesk-wol`

---

**Document Version**: 1.0.0  
**Last Updated**: 2026-02-10  
**Deployment Guide Maintainer**: Operations Team
