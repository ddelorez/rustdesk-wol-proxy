# Multi-Context Development Workflow: Phase 1 (WSL2) & Phase 2 (Windows)

**Document Purpose**: Guide developers through managing two separate development contexts for RustDesk WOL Proxy.

**Last Updated**: 2026-02-10

---

## Table of Contents

1. [Executive Overview](#executive-overview)
2. [Two-Context Development Model](#two-context-development-model)
3. [Context Architecture Diagram](#context-architecture-diagram)
4. [Directory Structure by Context](#directory-structure-by-context)
5. [How to Switch Between Contexts](#how-to-switch-between-contexts)
6. [Git Repository Organization](#git-repository-organization)
7. [CI/CD Strategy for Each Context](#cicd-strategy-for-each-context)
8. [Testing Across Contexts](#testing-across-contexts)
9. [Deployment Validation Workflow](#deployment-validation-workflow)
10. [Communication Between Contexts](#communication-between-contexts)

---

## Executive Overview

This project uses a **dual-context development strategy** to efficiently manage work across two very different environments:

- **Phase 1 Context (WSL2/Linux)**: Backend Flask API (WOL Proxy) development
- **Phase 2 Context (Native Windows)**: RustDesk Rust client fork development

### Why Two Contexts?

| Aspect | Phase 1 (API/Linux) | Phase 2 (Client/Windows) |
|--------|-------------------|---------------------------|
| **Development OS** | Ubuntu 22.04 (WSL2) | Windows 10/11 |
| **Language** | Python 3.8+ | Rust 1.7x+ |
| **Build Tools** | pip, pytest, Flask | Cargo, MSVC, Windows SDK |
| **Deployment Target** | Linux server (prod) | Windows endpoint clients |
| **Architecture** | REST API server | GUI desktop application |
| **Compilation** | Python (interpreted) | Rust (native Windows binary) |

**Key Insight**: These are fundamentally different development environments. Keeping them separate reduces context-switching overhead and toolchain conflicts.

---

## Two-Context Development Model

### Phase 1 Context: WSL2/Linux API Development

**Environment Details**:
- Host: WSL2 Ubuntu 22.04 (on Windows machine)
- Tools: Python 3.8+, Flask, pytest, Git
- Build artifact: `app.py` (interpreted, runs on Linux server)
- Deployment: Via systemd service on 10.10.10.145

**Responsibilities**:
- WOL packet transmission logic
- API request/response handling
- Logging and audit trails
- Unit & integration testing

**Execution Flow**:
```
Developer in WSL2 → Edit Python code → Run pytest → Test via curl → 
Git commit → CI/CD builds (if automated) → Deploy to production Linux server
```

### Phase 2 Context: Native Windows Rust Development

**Environment Details**:
- Host: Windows 10/11 (native)
- Tools: Rust toolchain, MSVC, CMake, Windows SDK
- Build artifact: `rustdesk.exe` (native Windows binary)
- Deployment: Via installer or custom binary distribution

**Responsibilities**:
- RustDesk client modifications
- Offline detection logic
- WOL API integration & retry strategy
- Windows-native UI updates

**Execution Flow**:
```
Developer on Windows → Edit Rust code in IDE → cargo build --release → 
Test locally (or via remote RustDesk server) → Git commit → GitHub Actions CI → 
Distribute custom builds to pilot users
```

### Context Relationship

```
Phase 1 (API)                          Phase 2 (Client)
┌──────────────────────────────────┐   ┌──────────────────────────────────┐
│ WSL2 Ubuntu 22.04                │   │ Windows 10/11 Native             │
│                                  │   │                                  │
│ ├─ Flask REST API                │   │ ├─ RustDesk fork (Rust)          │
│ ├─ Python business logic         │   │ ├─ Windows UI integration        │
│ ├─ WOL packet transmission       │←──┼─ WOL API client logic           │
│ ├─ Logging & audit              │   │ ├─ Offline detection             │
│ └─ Port 5001 HTTP               │   │ └─ Retry & user notifications    │
│                                  │   │                                  │
│ Runs on: 10.10.10.145 (prod)    ├──→├─ Calls API via HTTP/HTTPS       │
│                                  │   │                                  │
└──────────────────────────────────┘   └──────────────────────────────────┘
```

---

## Context Architecture Diagram

### Network Communication Topology

```
                    INTERNET / OFFSITE NETWORK
                            │
                    ┌───────┴─────────┐
                    │                 │
              ┌─────▼──────┐   ┌──────▼──────┐
              │ Offsite     │   │ Offsite     │
              │ RustDesk    │   │ RustDesk    │
              │ Clients     │   │ Clients     │
              │(Phase 2)    │   │(Phase 2)    │
              └─────┬──────┘   └──────┬──────┘
                    │                 │
                    │ HTTP/HTTPS      │ HTTP/HTTPS
                    │ /wake?id=X      │ /wake?id=Y
                    └────────┬────────┘
                             │
                    [Network Firewall/VPN/NAT]
                             │
                    ┌────────▼────────────────────┐
                    │   LOCAL NETWORK             │
                    │   10.10.10.0/24             │
                    │                            │
                    │  ┌─────────────────────┐  │
                    │  │ Flask WOL Proxy API │  │
                    │  │ (Phase 1)           │  │
                    │  │ 10.10.10.145:5001   │  │
                    │  └────────┬────────────┘  │
                    │           │               │
                    │           │ UDP :9        │
                    │           │ Broadcast     │
                    │           ▼               │
                    │  ┌────────────────────┐  │
                    │  │ LAN Broadcast      │  │
                    │  │ 255.255.255.255:9  │  │
                    │  └────────┬───────────┘  │
                    │           │              │
                    │  ┌────────┴──────────┐  │
                    │  │   Sleeping Hosts  │  │
                    │  │ (Wake-on-LAN      │  │
                    │  │ enabled)          │  │
                    │  └───────────────────┘  │
                    │                         │
                    └─────────────────────────┘
```

### Developer Workstations (Contexts)

```
╔════════════════════════════════════════════════════════════════════╗
║                     DEVELOPER MACHINE (Windows)                   ║
║                                                                   ║
║  ┌──────────────────────────────┐    ┌──────────────────────────┐ ║
║  │ Context 1: WSL2 Terminal     │    │ Context 2: PowerShell    │ ║
║  │ PATH: /mnt/c/.../p1-api/     │    │ PATH: C:\dev\rustdesk\   │ ║
║  │                              │    │                          │ ║
║  │ $ python src/app.py          │    │ PS> cargo build --releas│ ║
║  │ $ pytest tests/              │    │ PS> .\target\release\..  │ ║
║  │ $ curl localhost:5001/wake   │    │                          │ ║
║  │                              │    │                          │ ║
║  └──────────────────────────────┘    └──────────────────────────┘ ║
║   Port 5001 (local testing)          Windows GUI builds           ║
║                                                                   ║
║  ┌──────────────────────────────────────────────────────────────┐ ║
║  │ Shared: Git repository (C:\dev\rustdesk-wol-proxy)          │ ║
║  │  ├─ src/app.py (Phase 1 working copy)                       │ ║
║  │  ├─ fork/rustdesk/ (Phase 2 working copy, separate)         │ ║
║  │  └─ docs/ (shared documentation)                            │ ║
║  │                                                              │ ║
║  │ .gitignore isolates Phase 1 build artifacts from Phase 2    │ ║
║  └──────────────────────────────────────────────────────────────┘ ║
║                                                                   ║
╚════════════════════════════════════════════════════════════════════╝
```

---

## Directory Structure by Context

### Phase 1 (WSL2) Directory Organization

```
/mnt/c/dev/rustdesk-wol-proxy/  (or ~/rustdesk-wol-proxy)
├── src/
│   └── app.py                    ← Phase 1: Flask API code
├── config/
│   ├── .env.example
│   └── rustdesk-wol.service      ← Phase 1: Systemd service
├── tests/
│   ├── run_all_tests.py          ← Phase 1: Test suite
│   ├── test_comprehensive.sh
│   └── README.md
├── docs/
│   ├── PHASE2_DUAL_CONTEXT_WORKFLOW.md
│   ├── PHASE2_WINDOWS_SETUP.md
│   ├── API.md
│   ├── ARCHITECTURE.md
│   └── ... (shared documentation)
├── requirements.txt              ← Phase 1: Python dependencies
├── venv/                         ← Phase 1: Python virtual environment
│   └── (created by: python3 -m venv venv)
├── .gitignore
└── README.md
```

**Phase 1 Working Area**:
- Main development happens in `src/app.py`
- All Python work in WSL2 terminal
- Virtual environment: `source venv/bin/activate`
- Tests run via `pytest tests/`

### Phase 2 (Windows) Directory Organization

```
C:\dev\rustdesk\                 (separate clone from Phase 1 repo)
├── src/
│   ├── bin\
│   │   └── rustdesk.rs          ← Phase 2: Main binary entry
│   ├── client.rs                ← Phase 2: Modifications here
│   ├── platform\
│   │   └── windows\             ← Phase 2: Windows-specific code
│   └── ... (other Rust source)
├── Cargo.toml                    ← Phase 2: Rust manifest
├── Cargo.lock
├── target/
│   └── release\                  ← Phase 2: Windows binaries output
│       └── rustdesk.exe
├── build/
│   └── windows\                  ← Phase 2: Windows build scripts
└── .git/                         ← Separate fork repository
```

**Phase 2 Working Area**:
- Development in Rust source files
- All work in native Windows terminal (PowerShell/CMD)
- Build via `cargo build --release --target x86_64-pc-windows-msvc`
- Binaries output to `target/release/`

### Repository Clone Strategy

**Option A: Single Repo with Git Worktrees** (Recommended for this project)

```
C:\dev\
├── rustdesk-wol-proxy\           ← Main clone (Phase 1 API)
│   ├── src/app.py
│   ├── .git/
│   └── ... (as shown above)
└── rustdesk-wol-proxy-phase2\    ← Git worktree (Phase 2 client)
    └── (linked to Phase 1 .git, separate working tree)
```

**Setup**:
```powershell
# In C:\dev\rustdesk-wol-proxy (Phase 1 clone)
git worktree add ..\rustdesk-wol-proxy-phase2 phase2-client-fork
```

**Option B: Separate Repos** (If you maintain fork separately)

```
C:\dev\
├── rustdesk-wol-proxy\           ← Phase 1 (upstream API)
│   └── origin: your-fork/rustdesk-wol-proxy
└── rustdesk\                     ← Phase 2 (RustDesk fork)
    └── origin: your-fork/rustdesk
```

---

## How to Switch Between Contexts

### Quick Reference: Context Switching Checklist

**Switch FROM Phase 1 TO Phase 2**:

```powershell
# In WSL2 (Phase 1)
$ git status              # Ensure uncommitted work is saved
$ exit                    # Exit WSL2

# On Windows (Phase 2)
PS> cd C:\dev\rustdesk
PS> cargo build --release
```

**Switch FROM Phase 2 TO Phase 1**:

```powershell
# In PowerShell (Phase 2)
PS> git status           # Ensure uncommitted work is saved
PS> # Use Ubuntu app or WSL terminal shortcut

# In WSL2 (Phase 1)
$ cd ~/rustdesk-wol-proxy
$ source venv/bin/activate
$ python src/app.py
```

### Context 1: Phase 1 API Development (WSL2)

#### Start Phase 1 Work Session

```bash
# Open WSL2 terminal (or use VS Code WSL terminal)
wsl
# or from PowerShell: wsl.exe

# Activate virtual environment
cd ~/rustdesk-wol-proxy
source venv/bin/activate

# Set environment variables
export WOL_API_KEY="test_key_1234567890_secure"
export LOG_FILE="./dev.log"

# Start development server
python src/app.py
# API running at http://localhost:5001/health
```

#### Test Phase 1 API

```bash
# In another WSL2 terminal tab
curl -s http://localhost:5001/health | jq .

curl -s "http://localhost:5001/wake?id=test123&key=test_key_1234567890_secure" | jq .

# Run full test suite
pytest tests/ -v
```

#### Commit Phase 1 Changes

```bash
# Still in WSL2
git add src/app.py tests/

git commit -m "feat: add request ID tracking to WOL API"

git push origin main
```

### Context 2: Phase 2 Client Development (Windows)

#### Start Phase 2 Work Session

```powershell
# Open PowerShell (native Windows) or VS Code terminal

cd C:\dev\rustdesk

# Set environment (if needed)
$env:RUST_BACKTRACE = "1"

# Build in debug mode (faster)
cargo build --target x86_64-pc-windows-msvc

# Or build release (optimized)
cargo build --release --target x86_64-pc-windows-msvc
```

#### Test Phase 2 Build

```powershell
# Run binary
.\target\debug\rustdesk.exe

# Or after release build:
.\target\release\rustdesk.exe

# Run tests
cargo test --target x86_64-pc-windows-msvc
```

#### Commit Phase 2 Changes

```powershell
# In PowerShell (Windows)
git status

git add src/client.rs

git commit -m "feat: add WOL API response handling"

git push origin phase2-wol-integration
```

---

## Git Repository Organization

### Branch Strategy

**Phase 1 Branches**:
```
main (production-ready API code, deployed to 10.10.10.145)
  └─ develop (staging, pre-production testing)
       ├─ feature/health-check
       ├─ feature/structured-logging
       └─ bugfix/api-key-validation
```

**Phase 2 Branches**:
```
phase2-wol-integration (main client development branch)
  ├─ ph2-feature/offline-detection
  ├─ ph2-feature/wol-retry-logic
  └─ ph2-bugfix/ui-notification-timing
```

### Commit Strategy: Separate Concerns

**Phase 1 Commits** (message prefix: `[phase1]` or `[api]`):
```
[phase1] feat: add API rate limiting middleware
[phase1] test: add security validation tests
[phase1] docs: update deployment runbook
```

**Phase 2 Commits** (message prefix: `[phase2]` or `[client]`):
```
[phase2] feat: detect offline connection state
[phase2] feat: invoke WOL API on offline detection
[phase2] test: verify retry backoff logic
```

### Keeping Contexts In Sync

**Shared Components** (docs, CI/CD configs):
```
docs/                     ← Update from BOTH contexts
├── PHASE2_DUAL_CONTEXT_WORKFLOW.md
├── CONTEXT_SWITCHING_GUIDE.md
└── README.md

.github/workflows/        ← Update when CI scripts change
├── test-phase1.yml
└── test-phase2.yml
```

**Don't Merge Between Contexts** (keep independent):
- Phase 1 changes should NOT be force-merged into Phase 2 branch
- Phase 2 changes should NOT bloat Phase 1 repository
- Use separate working trees or repos to prevent accidental mixing

---

## CI/CD Strategy for Each Context

### Phase 1: API CI/CD Pipeline (Linux/WSL2)

**Trigger**: Commit to `develop` or PR to `main`

```yaml
# .github/workflows/test-phase1.yml
name: Phase 1 API Tests

on:
  push:
    branches: [main, develop]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'requirements.txt'
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.8'
      - run: |
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt
      - run: |
          source venv/bin/activate
          pytest tests/ -v --cov=src
      - uses: codecov/codecov-action@v3
```

**Deployment** (after merge to `main`):
```bash
# Run on 10.10.10.145 (production)
cd /opt/rustdesk-wol-proxy
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart rustdesk-wol
sudo systemctl status rustdesk-wol
```

### Phase 2: Client CI/CD Pipeline (Windows/Rust)

**Trigger**: Commit to Phase 2 branch or PR

```yaml
# .github/workflows/test-phase2.yml
name: Phase 2 Client Build

on:
  push:
    branches: [phase2-*]
  pull_request:
    branches: [phase2-*]

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          target: x86_64-pc-windows-msvc
      - run: |
          cargo build --release --target x86_64-pc-windows-msvc
      - run: |
          cargo test --target x86_64-pc-windows-msvc
      - uses: actions/upload-artifact@v3
        with:
          name: rustdesk-windows-binary
          path: target/release/rustdesk.exe
```

**Deployment** (via custom binary distribution):
- Upload artifact to release page
- Distribute to pilot users
- Gather feedback before wider rollout

---

## Testing Across Contexts

### Phase 1: API Testing (Unit & Integration)

**Unit Tests** (WSL2):
```bash
$ cd ~/rustdesk-wol-proxy && source venv/bin/activate
$ pytest tests/test_app.py -v
```

**Integration Tests** (Local network):
```bash
$ # Start API in one terminal
$ python src/app.py

$ # In another terminal, test from Windows
$ curl -s "http://localhost:5001/wake?id=test&key=secure_key"
```

### Phase 2: Client Testing (Rust + Integration)

**Unit Tests** (Windows):
```powershell
PS> cd C:\dev\rustdesk
PS> cargo test --lib
```

**Integration Tests** (with Phase 1 API):
```powershell
PS> # Ensure Phase 1 API is running at http://10.10.10.145:5001
PS> cargo test --test integration_wol_api
```

### Cross-Context Testing: Phase 1 ↔ Phase 2

**Scenario 1: Test API from Phase 2 Client**

```powershell
# Phase 2: From Windows machine running custom RustDesk client
# Simulate offline detection and call WOL API

PS> $url = "http://10.10.10.145:5001/wake?id=desk1&key=$env:WOL_API_KEY"
PS> $response = Invoke-WebRequest -Uri $url
PS> $response.Content | ConvertFrom-Json | Format-Table
```

**Scenario 2: Verify API Response with Phase 2 Integration**

```bash
# Phase 1: Test that API response is compatible with Phase 2 client expectations
$ curl -s "http://10.10.10.145:5001/wake?id=desk1&key=$WOL_API_KEY" | jq .

# Expected response that Phase 2 client will parse:
# {
#   "status": "success",
#   "message": "Wake-on-LAN packet sent to ...",
#   "timestamp": "2026-02-10T21:07:46.182Z"
# }
```

### Test Configuration by Context

**Phase 1 Test Config** (`tests/` directory):
```
tests/
├── run_all_tests.py        # Master test runner
├── test_app.py             # Flask endpoint tests
├── test_wol_packet.py      # WOL logic tests
├── test_validation.py      # Input validation tests
└── README.md
```

**Phase 2 Test Config** (`C:\dev\rustdesk\tests\`):
```
tests/
├── integration/
│   ├── wol_api_client.rs        # Test WOL API HTTP client
│   └── offline_detection.rs     # Test offline scenario
├── unit/
│   ├── retry_logic.rs
│   └── ui_notification.rs
└── fixtures/
    └── mock_wol_responses.json
```

---

## Deployment Validation Workflow

### Validation Checklist: Phase 1 API (Production Linux Server)

**Before Merging to `main`**:

- [ ] All tests pass: `pytest tests/ -v --cov=src`
- [ ] Code review completed and approved
- [ ] Deployment procedure documented
- [ ] API key rotation plan defined
- [ ] Backup of current production API created

**During Deployment** (on 10.10.10.145):

```bash
# 1. Backup current version
sudo systemctl stop rustdesk-wol
sudo cp -r /opt/rustdesk-wol-proxy /opt/rustdesk-wol-proxy.backup.$(date +%Y%m%d)

# 2. Update code
cd /opt/rustdesk-wol-proxy
git fetch origin
git checkout main
git pull

# 3. Update dependencies (if changed)
source venv/bin/activate
pip install -r requirements.txt

# 4. Start service
sudo systemctl start rustdesk-wol
sudo systemctl status rustdesk-wol

# 5. Verify health
curl http://localhost:5001/health
```

**Post-Deployment Validation**:

- [ ] Health endpoint returns `healthy` status
- [ ] API responds to valid `/wake` requests with HTTP 200
- [ ] Logs show zero errors in first 5 minutes
- [ ] Can connect from offsite client (if external exposure enabled)
- [ ] WOL packets successfully sent to test machine

### Validation Checklist: Phase 2 Client (Windows Distribution)

**Before Release to Pilot Users**:

- [ ] All tests pass: `cargo test --release`
- [ ] Build succeeds on Windows: `cargo build --release`
- [ ] Binary signed (future enhancement)
- [ ] User manual prepared
- [ ] Pilot user list defined (5-10 users)

**During Distribution**:

```powershell
# 1. Build final binary
cargo build --release --target x86_64-pc-windows-msvc

# 2. Verify binary works locally
.\target\release\rustdesk.exe --version

# 3. Sign binary (if code signing enabled)
signtool sign /f cert.pfx .\target\release\rustdesk.exe

# 4. Create installer or distribute binary
# Option A: Distribute .exe directly
# Option B: Create installer (.msi)
# Option C: Post to GitHub release

# 5. Provide installation instructions to pilot users
```

**Post-Distribution Validation**:

- [ ] Pilot users report successful installation
- [ ] Clients connect to RustDesk server
- [ ] Offline detection works as expected
- [ ] WOL API is called when offline detected
- [ ] Machine wakesup successfully
- [ ] No unexpected crashes or errors
- [ ] Gather feedback for refinement

### Smoke Test Across Contexts

**Automated Smoke Test** (after each context deployment):

```bash
#!/bin/bash
# Phase 1: Run after API deployment

echo "=== Phase 1 API Smoke Test ==="
API_URL="http://10.10.10.145:5001"
API_KEY="$WOL_API_KEY"

# Test health
if curl -s "$API_URL/health" | grep -q "healthy"; then
    echo "✓ API health check passed"
else
    echo "✗ API health check failed"
    exit 1
fi

# Test wake endpoint
RESPONSE=$(curl -s "$API_URL/wake?id=test_device&key=$API_KEY")
if echo "$RESPONSE" | grep -q "success"; then
    echo "✓ WOL endpoint responding"
else
    echo "✗ WOL endpoint failed"
    exit 1
fi

echo "=== Smoke test complete ==="
```

---

## Communication Between Contexts

### Phase 1 → Phase 2: API Specification

**What Phase 2 Needs to Know**:

1. **API Endpoint**: `http://10.10.10.145:5001/wake` (or HTTPS via proxy)
2. **Authentication**: Query parameter `key=<API_KEY>`
3. **Device Parameter**: Query parameter `id=<RUSTDESK_ID>`
4. **Response Format**: JSON with `status`, `message`, `timestamp`
5. **Error Handling**: HTTP status codes (200, 400, 403, 404, 500)

**Example Integration** (Phase 2 Rust code):

```rust
// Phase 2: RustDesk client calling Phase 1 API
async fn wake_machine_via_wol(device_id: &str) -> Result<()> {
    let api_key = get_wol_api_key_from_config();  // From settings
    let api_url = "http://10.10.10.145:5001/wake";
    
    let url = format!(
        "{}?id={}&key={}",
        api_url, device_id, api_key
    );
    
    let response = reqwest::Client::new()
        .get(&url)
        .send()
        .await?;
    
    if response.status() == 200 {
        println!("Machine waking up...");
        Ok(())
    } else {
        Err("WOL request failed".into())
    }
}
```

### Phase 2 → Phase 1: Requirements Specification

**What Phase 1 Needs to Know**:

1. **Response Time**: Phase 2 expects response within 5 seconds
2. **MAC Accuracy**: Ensure MAC address mapping is current
3. **Reliability**: 99% success rate for WOL transmission
4. **Rate Limits**: Can handle up to 10 requests/minute per client
5. **Logging**: Request/response details for debugging

### Shared Documentation

**Both contexts reference**:
- `docs/CONTEXT_SWITCHING_GUIDE.md` (this document)
- `docs/API.md` (API contract)
- `README.md` (overall project)

**Context-Specific Documentation**:
- Phase 1: `docs/DEPLOYMENT.md`, `docs/QUICK_START.md`
- Phase 2: `docs/PHASE2_WINDOWS_SETUP.md`, `docs/PHASE2_DESIGN.md`

---

## Summary

This dual-context workflow provides:

✅ **Clear separation** between API development (Phase 1) and client development (Phase 2)

✅ **Independent toolchains** (Python + Flask vs. Rust + MSVC)

✅ **Minimal context-switching overhead** (developers stay in their native environment)

✅ **Parallel development** (two developers can work simultaneously on different phases)

✅ **Integration points** (well-defined API contract between contexts)

✅ **Automated validation** (CI/CD pipelines test each context independently)

For quick context switching, refer to [`CONTEXT_SWITCHING_GUIDE.md`](CONTEXT_SWITCHING_GUIDE.md).

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-10  
**Status**: Active  
**Next Review**: Phase 2.1 Completion
