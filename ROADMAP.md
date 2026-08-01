# Roadmap

## Current Status — v1.0.0

Core functionality complete: decentralized mesh-based evacuation routing
with on-device Dijkstra, dual-path sensor fusion, and real-time 3D digital twin.

## Near-Term (3–6 months)

### Performance & Reliability
- [ ] Firmware OTA update mechanism for field-deployed nodes
- [ ] Non-volatile link-state recovery after power loss
- [ ] Configurable node graph loading from SD/flash (remove hardcoded topology)
- [ ] Formal worst-case timing analysis with oscilloscope validation

### Protocol Enhancements
- [ ] End-to-end encryption for ESP-NOW hazard packets
- [ ] Adaptive TTL based on mesh diameter heuristics
- [ ] Priority queuing (evacuation commands > telemetry)

### Testing & Validation
- [ ] Hardware-in-the-loop (HIL) test fixture with 15-node mesh
- [ ] Automated CI pipeline with GitHub Actions
- [ ] Fuzz testing for packet corruption resilience
- [ ] Formal verification of hold-down hysteresis safety properties

## Medium-Term (6–12 months)

### Hardware Expansion
- [ ] Sub-GHz LoRa mesh layer for concrete/metal penetration
- [ ] ESP32-S3 port with hardware accelerators for TinyML
- [ ] Battery-backed node design with power monitoring
- [ ] Integration with commercial fire alarm panels (BACnet)

### Advanced Features
- [ ] TinyML flashover prediction (30–60s before thermal runaway)
- [ ] Occupant counting via BLE/Wi-Fi probe requests
- [ ] Dynamic stairwell pressurization monitoring
- [ ] Multi-lingual voice guidance integration

### Platform
- [ ] Web-based building graph editor (drag-and-drop)
- [ ] Building Information Model (BIM) import (IFC format)
- [ ] Mobile companion app for first responders
- [ ] Multi-building campus coordination

## Long-Term (1–2 years)

### Ecosystem
- [ ] Open-source reference hardware design (KiCad)
- [ ] Certified UL/EN compliance roadmap
- [ ] Integration with municipal emergency systems
- [ ] AR navigation for firefighters (streamed safest-entry routes)

### Scale
- [ ] Hierarchical mesh for 500+ node deployments
- [ ] Cross-building coordination via cloud relay
- [ ] Predictive evacuation using digital twin simulation

---

*This roadmap is aspirational and reflects the project's vision.
Priorities may shift based on community feedback and funding.*