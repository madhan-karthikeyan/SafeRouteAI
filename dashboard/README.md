# SafeRouteAI — Fire Commander Emergency Dashboard

Node-RED visual dashboard for emergency responders and building operations control (EOC).

## Features

- **2D Floor Grid View**: Displays live status of all structural nodes color-coded by safety status:
  - 🟢 **Safe**: Normal sensor readings & optimal evacuation route.
  - 🟡 **Warning**: High smoke density / alternate reroute active.
  - 🔴 **Danger**: Flame detected / immediate hazard zone.
  - ⚪ **Shelter-In-Place**: Strobe animation when all exits are blocked.
- **Node Health Panel**: Real-time monitoring of sensor health, failover tiers (Primary, Consensus, Static Default), and network status.
- **REST API Endpoints**: Exposes `/evac/api/nodes` and `/evac/api/health` for external monitoring tools.

## Quick Start (Docker)

```bash
# Start Mosquitto and Node-RED containers
cd docker
docker-compose up -d mosquitto nodered

# Open Node-RED editor
# URL: http://localhost:1880

# Access dashboard UI
# URL: http://localhost:1880/ui
```

## Importing Flows

1. Open `http://localhost:1880` in your web browser.
2. Click the top-right hamburger menu → **Import**.
3. Select `dashboard/flows.json` and click **Import**.
4. Click **Deploy**.
