# Dynamic Fire Evacuation Router with Real-Time Hazard Mapping

## Problem Background

In large commercial facilities, standard static emergency exit signs can lead occupants directly into danger if a fire breaks out between them and that exit. Toxic smoke inhalation, structural damage, and rapid flashovers happen in minutes. To minimize casualties, modern buildings require intelligent life-safety infrastructure: decentralized node networks that detect fire spread, communicate hazard vectors locally, and dynamically update visual evacuation paths in real time.

---

## Clear Objective

Design and build a localized module which must continuously ingest data from multiple localized fire sensors, compute a dynamically updating safest exit path based on a simulated indoor layout, and drive an intelligent visual indicator matrix to guide occupants away from active hazards.

---

# Technical Requirements & Multi-Sensor Inputs

## Hardware Platform

- ESP32
- STM32
- Raspberry Pi Pico W

## Multi-Sensor Ingestion (Simulated)

The system must process concurrent inputs representing distinct vectors of a fire hazard. Teams must demonstrate how their system responds to each of the following:

### Thermal Vector (Temperature)

- Reading ambient thermal rise
- Via DHT22, thermistors, or simulated analog inputs

### Particulate Vector (Smoke/Gas)

- Reading gas concentration and air quality degradation
- Via MQ-2, MQ-135, or simulated inputs

### Optical Vector (Flame Detection)

- Reading immediate radiant infrared light from an active flame
- Via an IR flame sensor or digital switch

### Occupancy Data

- Access control system
- Cameras
- Etc.
- Feel free to simulate it.

---

## Actuators & Dynamic Indicators

- Visual indicator
- Local buzzer
- Audio module for audible distress signaling

---

# Edge Processing & Algorithm

## Dynamic Pathfinding Algorithm

Implement a lightweight routing logic (such as simplified Dijkstra, A*, or a weighted state-machine grid) directly on the microcontroller.

---

## Sensor Fusion & Dynamic Weight Calculation

The system must **not** rely on simple binary thresholds.

The cost (weight) of traversing a specific hallway segment must increase **exponentially** based on a mathematical formula combining:

- Temperature (°C)
- Smoke Density (PPM)
- Flame Presence (Boolean)

or other parameters.

---

## Real-Time Path Update

If an exit pathway becomes blocked or highly hazardous based on sensor calculations, the MCU must instantly:

- Recalculate the evacuation path
- Reverse the animation direction of the LED strip
- Change LED colors

Example:

- 🟢 Green → Safe path
- 🔴 Pulsing Red → Immediate danger
- 🟡 Yellow → High-smoke alternate route

Teams should also consider:

- Number of occupants
- Occupant density
- Floor information

while designing the optimum evacuation path.

---

## Algorithm Data & Resource Optimization

Teams are highly encouraged to use online open-source repositories and public datasets such as:

- NIST Fire Data
- Kaggle fire/smoke time-series datasets
- GitHub repositories

to study and extract:

- realistic fire-spread profiles
- gas PPM curve changes
- temperature progression timelines

to fine-tune sensor fusion weights.

---

# Demonstration & Simulation Framework

## Advantageous Use of Simulation

Teams are encouraged to build a digital twin or software injector tool using:

- Python scripts
- Processing IDE
- Node-RED UI
- Serial terminal

that broadcasts simulated multi-sensor data streams directly into the MCU network.

---

## Live Test Case

During testing, judges will select a specific zone on the simulator interface to trigger a **Flashover** (high heat + high smoke).

The physical or simulated hardware node corresponding to that zone must instantly:

- Receive the simulated payload
- Fuse it with local physical sensor readings
- Immediately reroute the physical LED strips / visual indicators across the network to safely guide occupants away.

---

# Deliverables

> ZIP all files before submission.

## 1. Simulation / Injection Tool

A software tool or dashboard capable of simulating and injecting varied fire timelines, including:

- Slow smoldering
- Fast flashover

across multiple structural nodes.

---

## 2. Firmware Source Code

Modular:

- C/C++
- MicroPython

code featuring:

- Non-blocking pathfinding algorithms
- Smooth concurrent LED animation loops

---

## 3. Fire Commander Dashboard

A central monitoring dashboard (Node-RED or ThingsBoard) showing:

- 2D floor grid layout
- Live hazard nodes
- Current calculated exit paths
- System health status

Target scenario:

- Multi-story commercial building

Cloud-based applications may be used for visualization.

---

## 4. Engineering Report & Presentation

Include:

- Detailed flowchart
- Sensor threshold explanation
- Dynamic edge-weight calculations
- Pitch deck
- Real-world scalability discussion

You must also submit a presentation using the provided template with relevant slides completed.

---

## Submission Notes

- Upload using the **Upload Files** button.
- Accepted formats:
  - PDF
  - ZIP
- If ZIP upload fails, convert/print files to PDF and upload.

---

# Evaluation Criteria

## 1. Algorithm Responsiveness & Sensor Fusion (30%)

- Speed and accuracy of routing logic
- Must update within **300 ms** of a state change
- Mathematical weighting using:
  - Temperature
  - Smoke
  - Flame

---

## 2. Simulation Quality & Demonstration (20%)

- Execution of test scenarios
- Sophisticated simulator capable of injecting custom fire timelines into hardware nodes

---

## 3. Visual Interface & Usability Clarity (15%)

- Clear LED matrix / LED strip animations
- Chasing light patterns
- Easy-to-understand evacuation guidance

---

## 4. Solution Pitch & Presentation (15%)

Evaluation based on:

- Clarity of thought
- Commercial viability
- Technical justification
- System architecture
- Q&A handling

---

## 5. Multi-Node Communication Logic (10%)

Robust communication using protocols such as:

- ESP-NOW
- MQTT
- BLE Mesh

to share localized hazard vectors.

---

## 6. Fail-Safe Operation (10%)

Ability to handle:

- Communication drops
- Corrupted simulation payloads
- Sensor failures

Example:

- Falling back to default safe evacuation paths when communication fails.