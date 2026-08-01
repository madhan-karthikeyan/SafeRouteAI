# SafeRouteAI — Setup Guide

## Prerequisites

| Dependency | Version | Purpose |
|---|---|---|
| PlatformIO Core | ≥6.0 | ESP32 firmware build & flash |
| Python | ≥3.10 | Backend API + simulator + tests |
| Node.js | ≥18 | Frontend dev server (or Bun) |
| Bun | ≥1.2 | Faster alternative to Node.js (recommended) |
| Docker + Compose | latest | Mosquitto MQTT + containerized stack |
| ESP32 Dev Board | any | Firmware target (optional for dev) |
| Git | ≥2.30 | Version control |

---

## Development Environment

### 1. VS Code Extensions

Install these from the marketplace:

- **PlatformIO IDE** — firmware editing, build, flash, serial monitor
- **Python** (ms-python.python) — linting, type checking, venv management
- **ESLint** — frontend linting
- **Prettier** — frontend formatting
- **Docker** — container management

### 2. Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

### 3. Install Bun (if not present)

```bash
curl -fsSL https://bun.sh/install | bash
# Verify:
bun --version
```

---

## Project Setup

All commands run from the repository root.

### Backend

```bash
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Dependencies: `fastapi`, `uvicorn[standard]`, `paho-mqtt`, `websockets`

### Frontend

```bash
cd frontend && bun install
# Or with npm: npm install
```

Dependencies: React 19, TypeScript, Vite, TanStack Router, R3F (Three.js), Tailwind CSS v4, Zustand, Recharts, Framer Motion, Radix UI

### Firmware (PlatformIO)

```bash
# PlatformIO auto-installs library dependencies on first build:
pio run --environment esp32dev
```

Libraries: FastLED, PubSubClient

### Simulator

```bash
source .venv/bin/activate
pip install -r simulator/requirements.txt
```

Dependencies: `pyserial`, `paho-mqtt`, `numpy`, `scipy`

### Docker Stack

```bash
docker-compose up -d
```

Starts: Mosquitto (port 1883, 9001), Backend (port 8000), Frontend (port 5173), Node-RED dashboard (port 1880)

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_USE_MOCK` | No | `true` | `true` = standalone mock engine; `false` = connect to real backend |
| `VITE_API_BASE` | No | `http://localhost:8000` | Backend REST API URL |
| `VITE_WS_URL` | No | `ws://localhost:8000/api/events` | WebSocket URL for snapshot stream |
| `MQTT_BROKER` | No | `localhost` | Mosquitto broker hostname |
| `MQTT_PORT` | No | `1883` | Mosquitto broker port |

The `.env` file at `frontend/.env` sets `VITE_USE_MOCK=true` by default. Copy `frontend/.env.example` and adjust:

```bash
cp frontend/.env.example frontend/.env
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `bun install` fails on native deps | Missing build tools | `apt install build-essential` or use `npm install` |
| WebSocket connection refused | Backend not running | Start with `uvicorn backend.main:app --reload --port 8000` |
| MQTT connection timeout | Mosquitto container not running | `docker-compose up -d mosquitto` |
| Firmware flash fails | Wrong board/port | Check `platformio.ini` board setting and USB port |
| Frontend shows empty scene | Missing building assets | Verify `frontend/src/assets/buildings/` has `index.json` and building directories |
| `pio test` fails | Test build flags missing | Use `pio test --environment esp32dev` |
| Python import errors | Wrong virtualenv | Activate `.venv` and reinstall requirements |
| Port conflicts | Another service on same port | Change `docker-compose.yml` host port mappings |

---

## Quick-Start Reference

```bash
# ── Backend ──
source .venv/bin/activate && uvicorn backend.main:app --reload --port 8000

# ── Frontend (dev) ──
cd frontend && bun run dev

# ── Frontend (build) ──
cd frontend && bun run build

# ── Firmware (build) ──
pio run --environment esp32dev

# ── Firmware (build + flash) ──
pio run --environment esp32dev --target upload

# ── Firmware (serial monitor) ──
pio device monitor --port /dev/ttyUSB0 --baud 115200

# ── Simulator injector CLI ──
python -m simulator.injector --cli

# ── Docker (full stack) ──
docker-compose up -d

# ── Docker (single service) ──
docker-compose up -d mosquitto

# ── Tests (all) ──
./scripts/run-all-tests.sh

# ── Tests (backend) ──
python -m pytest tests/backend/ -v

# ── Tests (firmware Python ref) ──
python tests/firmware/test_dijkstra.py

# ── Tests (simulator) ──
python tests/simulator/test_profiles.py

# ── Tests (integration) ──
python tests/integration/test_scenarios.py

# ── Lint (frontend) ──
cd frontend && bun run lint

# ── Format (frontend) ──
cd frontend && bun run format
```
