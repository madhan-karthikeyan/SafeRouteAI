# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.x     | ✅ Active development |

## Reporting a Vulnerability

SafeRouteAI is an embedded safety system. If you discover a security vulnerability,
please report it privately before disclosing it publicly.

**Do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to the project maintainers. You should
receive a response within 48 hours. If you do not, please follow up.

## What to Include

- Type of vulnerability
- Full description and impact
- Steps to reproduce
- Proof of concept (if available)
- Affected components (firmware, backend, protocol, etc.)

## Scope

- **Firmware**: ESP-NOW packet handling, sensor data validation, MQTT bridge
- **Backend**: API endpoints, WebSocket connections, MQTT ingestion
- **Protocol**: Packet format, sequence number handling, CRC validation
- **Infrastructure**: MQTT broker, Docker configuration

## Safety-Critical Disclosure

Since SafeRouteAI is intended for life-safety applications, vulnerabilities
that could affect evacuation routing decisions receive the highest priority.

## Preferred Encryption

PGP-encrypted reports are preferred. Contact maintainers for key details.