# RustDesk Auto-WOL Project

**Project Name:** RustDesk Self-Hosted Auto Wake-on-LAN  
**Status:** In Progress  
**Goal:** Enable seamless remote wake-up of asleep/offline machines for
offsite users using a custom-forked RustDesk client + lightweight backend
API.

---

## Project Overview

We are building a solution to solve the missing Wake-on-LAN (WOL)
functionality for **offsite** users when using a self-hosted RustDesk
server.

### Core Problem

RustDesk's built-in WOL only works on the local LAN. When machines are
asleep, offsite clients cannot wake them because WOL magic packets do not
route over the internet.

### Solution

- A small, secure **WOL Proxy API** running on the RustDesk server VM
  (10.10.10.145)
- A **forked/custom RustDesk client** that automatically detects offline
  peers, calls the WOL API, waits for boot, and retries the connection
- Clean git-based development workflow between workstation and server

---

## Current Status (Completed)

- RustDesk server (hbbs/hbbr) running bare-metal on Proxmox VM at
  **10.10.10.145** on LAN 10.10.10.0/24
- Confirmed server can send WOL packets (broadcast to 10.10.10.255
  works)
- Git repository created: `rustdesk-wol-proxy`
  - Repo is synced between server (`/opt/rustdesk-wol-proxy`) and
    workstation (VS Code + WSL2)
  - `.gitignore`, `README.md`, `requirements.txt` in place
- Python virtual environment set up on both server and workstation
- Flask + gunicorn dependencies installed
- Basic project structure and development workflow established

---

## High-Level Architecture

Offsite User
↓ (RustDesk Client - custom fork)
[Detects offline ID] → HTTP GET /wake?id=XXXX&key=...
↓
RustDesk WOL API (Flask + gunicorn)
↓ (runs on 10.10.10.145)
Sends Magic Packet → LAN Broadcast (10.10.10.255:9)
↓
Target Machine wakes up → RustDesk service starts → registers with hbbs
↓
Client retries connection automatically after delay

**Components:**

- **Backend**: Flask API (`app.py`) with ID → MAC mapping
- **Security**: API key protection + optional reverse proxy (HTTPS)
- **Deployment**: Systemd service using gunicorn + venv
- **Frontend**: Forked RustDesk client (Flutter) with auto-wake logic
- **Logging**: Rotating log file + console output

---

## Plan & Roadmap

### Phase 1 – Backend API (Current Phase)

- [x] Git repo + sync workflow
- [ ] Finalize `app.py` (ID→MAC map, API key, logging, WOL function)
- [ ] Create systemd service (`rustdesk-wol.service`)
- [ ] Test API from external network
- [ ] Add basic authentication / rate limiting

### Phase 2 – Client Integration

- Fork RustDesk client
- Add settings for WOL API URL + key
- Hook into connection flow (detect offline → call API → delay → retry)
- Add UI feedback ("Waking machine…")
- Build custom client binaries

### Phase 3 – Polish & Alternatives

- Optional: Tailscale fallback
- Documentation for users
- Testing with multiple machines

---

## Technical Details

- **Server Path**: `/opt/rustdesk-wol-proxy`
- **Repo**: <https://github.com/ddelore/rustdesk-wol-proxy> (private)
- **LAN**: 10.10.10.0/24
- **Broadcast IP**: 10.10.10.255
- **Port**: 5001 (will be proxied)
- **Python**: venv-based (Flask + gunicorn)
- **RustDesk Server**: rustdesksignal.service + rustdeskrelay.service

---

## Open Items / Notes

- Collect all RustDesk IDs + corresponding MAC addresses
- Decide on final API key and whether to use reverse proxy (Nginx/Caddy) +
  HTTPS
- Measure average boot + registration time to set proper retry delay
- Decide on client fork depth (full fork vs lightweight wrapper)

---
