# SafeRouteAI — Fire Simulation & Injection Tool

The Python Fire Injector is a digital twin simulation engine capable of generating realistic multi-sensor fire timelines, broadcasting binary hardware packets over serial/ESP-NOW, and publishing telemetry payloads over MQTT.

## Features

- **Fire Profiles**:
  - `slow_smolder`: Gradual temperature rise (25°C → 90°C) and progressive smoke buildup (0 → 800 PPM) over 120s.
  - `flashover`: Rapid thermal spike (25°C → 275°C) and extreme smoke (2800 PPM) with flame trigger within 5s.
- **Judge Control & Event Injection**: Trigger manual flashover events on arbitrary structural zones/nodes.
- **Corrupt Packet Injection**: Generate intentional CRC failures (`corrupt` mode) to demonstrate mesh fail-safe rejection live.
- **MQTT Broadcasting**: Stream simulated sensor payloads directly to MQTT broker (`evac/node/<id>/hazard`).
- **Interactive CLI & Automated Modes**: Full terminal command interface for live demonstration control.

## Files

```
simulator/
├── data/
│   └── building_graph.json # Standard 6-node test topology
├── fire_profiles/
│   ├── flashover.py        # Flashover exponential curve generator
│   ├── slow_smolder.py    # Smolder linear/logistic growth curve
│   └── regression.py       # Offline curve fitting script for NIST/Kaggle datasets
├── graph_model.py          # Topology loader & per-node calibration model
├── injector.py             # Main CLI & MQTT simulation injector
├── requirements.txt        # Python dependencies
└── README.md
```

## Usage Instructions

### Single-Shot Hex Packet Generation
```bash
python3 simulator/injector.py --packet 1
```

### Interactive CLI Mode
```bash
python3 simulator/injector.py --cli
```
Available CLI Commands:
- `slow`: Set smolder profile.
- `flashover`: Trigger fast fire event.
- `zone <id>`: Target specific node/zone.
- `corrupt`: Enable corrupt packet mode (CRC = 0x0000).
- `clean`: Disable corrupt packet mode.
- `pub`: Broadcast current state to MQTT broker.
- `quit`: Exit injector.

### Live MQTT Injection
```bash
python3 simulator/injector.py --mqtt --broker localhost --profile flashover --zone 3
```

## Dataset Calibration Script

To run the offline dataset regression fitting script against NIST fire data:
```bash
python3 simulator/fire_profiles/regression.py
```
