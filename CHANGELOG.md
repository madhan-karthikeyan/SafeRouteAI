# Changelog

All notable changes to SafeRouteAI are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-27

### Added

#### Firmware (ESP32)
- On-device Dijkstra pathfinder with priority queue implementation
- Dual-path sensor fusion: EWMA slow path + rate-of-change fast path
- Continuous exponential edge cost formula (temperature, smoke, flame, occupancy)
- Double-buffered link-state table with atomic pointer swap (lock-free)
- ESP-NOW mesh flooding with sequence number anti-replay (RFC 1982)
- CRC16 packet validation on all incoming messages
- Three-tier sensor fail-safe: local → neighbor consensus → static default
- Hold-down hysteresis (1800ms) to prevent LED flicker
- FreeRTOS LED animation task on Core 1 (chase, pulse, strobe)
- MQTT gateway bridge for read-only telemetry
- Shelter-in-place detection when all paths exceed cost threshold

#### Backend (FastAPI)
- Multi-building graph topology server (5 commercial layouts)
- MQTT→WebSocket real-time bridge with 200ms snapshot interval
- IDW hazard heatmap interpolation per floor
- In-memory snapshot ring buffer for replay (600 snapshots)
- REST API: health, buildings, graph, inject, reset, demo, replay
- WebSocket endpoint for live digital twin streaming
- Simulation engine with Dijkstra validation and flame spread diffusion

#### Frontend (React + Three.js)
- 3D digital twin with React Three Fiber (R3F)
- Multi-building support with interactive selection
- Real-time node state visualization (color-coded spheres)
- Fire particle system and smoke volume rendering
- Evacuation route rendering with animated arrows
- Heatmap overlay per floor
- Node health panel with telemetry data
- Network statistics dashboard
- Fire injector control panel
- Mock mode for hardware-free development

#### Simulator (Python)
- Fire injector CLI with slow smolder and flashover profiles
- Zone-targeted injection and packet corruption
- MQTT publishing for hardware-in-the-loop testing
- Building graph model with JSON serialization
- Logistic and step-function fire growth curves

#### Dashboard (Node-RED)
- 2D floor grid with color-coded node status
- Node health monitoring panel
- Shelter-in-place status indicator

#### Documentation
- Architecture overview with system layers and communication flow
- Engineering report with cost formula and fail-safe hierarchy
- Multi-format slide decks (16-slide, 6-slide executive, SIH submission)
- Speaker notes with Q&A preparation

#### Infrastructure
- Docker Compose for Mosquitto + Backend + Frontend + Node-RED
- PlatformIO build configuration for ESP32
- Test suite: firmware (Unity C++), backend (Python), simulator, integration
- Shell scripts for build, test, and demo workflows