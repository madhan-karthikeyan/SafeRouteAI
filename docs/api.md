# SafeRouteAI API Reference

Base URL: `http://localhost:8000`

All endpoints accept an optional `buildingId` query parameter. When omitted, the default building `mega-mall` is used.

---

## `GET /api/health`

System health and status.

### Purpose
Returns backend health, number of active building simulations, WebSocket connection count, and tick loop status.

### Request
No parameters.

### Response
```json
{
    "status": "ok",
    "buildings": 1,
    "ws_connections": 3,
    "tick_running": true
}
```

### Fields
| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | Always `"ok"` when server is running |
| `buildings` | `int` | Number of building SimState instances created |
| `ws_connections` | `int` | Total active WebSocket connections across all buildings |
| `tick_running` | `bool` | Whether the 200ms simulation tick loop is active |

### Error Codes
| Code | Meaning |
|------|---------|
| 200 | OK |

---

## `GET /api/buildings`

List available building models with metadata.

### Purpose
Returns the building index loaded from `frontend/src/assets/buildings/index.json`. Each entry describes a building's type, floor count, room count, and exit count.

### Request
No parameters.

### Response
```json
[
    {
        "id": "mega-mall",
        "name": "Mega Shopping Mall",
        "type": "mall",
        "description": "Four-story mega mall with grand central atrium, 4 entrances...",
        "floors": 4,
        "totalRooms": 110,
        "totalExits": 7,
        "thumbnail": null,
        "source": "Architecturally plausible layout based on published mall floor plans",
        "sourceUrl": "https://en.wikipedia.org/wiki/Shopping_mall",
        "license": "CC BY 4.0 (SafeRouteAI)"
    },
    {
        "id": "city-hospital",
        "name": "City Hospital",
        "type": "hospital",
        ...
    }
]
```

### Fields (per building)
| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Unique building identifier |
| `name` | `string` | Human-readable building name |
| `type` | `string` | Building category (mall, hospital, office, university, airport) |
| `description` | `string` | Architectural description |
| `floors` | `int` | Number of floors |
| `totalRooms` | `int` | Number of rooms in the building |
| `totalExits` | `int` | Number of emergency exits |
| `thumbnail` | `string\|null` | Thumbnail image path (if any) |
| `source` | `string\|null` | Data source attribution |
| `sourceUrl` | `string\|null` | Source URL |
| `license` | `string\|null` | License information |

### Error Codes
| Code | Meaning |
|------|---------|
| 200 | OK |

---

## `GET /api/graph?buildingId=...`

Building graph topology.

### Purpose
Returns the full `BuildingGraph` for the specified building, including floor plans, node positions, edges, and hazard grid dimensions.

### Request Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `buildingId` | `string` | No | `mega-mall` | Building identifier |

### Response
```json
{
    "id": "mega-mall",
    "name": "Mega Shopping Mall",
    "floors": [
        {
            "index": 0,
            "name": "Ground Floor",
            "size": {"width": 80.0, "depth": 60.0},
            "origin": {"x": -40.0, "y": 0.0, "z": -30.0},
            "rooms": [
                {
                    "id": "zone-1",
                    "x": -30.0,
                    "z": -20.0,
                    "width": 10.0,
                    "depth": 8.0,
                    "label": "Entrance Lobby",
                    "type": "lobby"
                }
            ],
            "corridors": [
                {
                    "from": [-40.0, -30.0],
                    "to": [40.0, 30.0],
                    "width": 4.0
                }
            ]
        }
    ],
    "nodes": [
        {
            "id": "n-zone-1",
            "kind": "sensor",
            "floor": 0,
            "position": {"x": -25.0, "y": 0.4, "z": -16.0},
            "label": "Entrance Lobby"
        }
    ],
    "edges": [
        {
            "id": "e-corridor-1",
            "from": "n-zone-1",
            "to": "n-zone-2"
        }
    ],
    "hazardGrid": {
        "cols": 32,
        "rows": 22
    }
}
```

### Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Building ID |
| `name` | `string` | Building name |
| `floors` | `array` | Floor plan definitions with rooms and corridors |
| `nodes` | `array` | Graph nodes with position, kind, floor |
| `edges` | `array` | Graph edges connecting nodes |
| `hazardGrid` | `object` | Grid dimensions (`cols`: 32, `rows`: 22) |

### Node Kinds
| Kind | Description |
|------|-------------|
| `sensor` | Standard sensor-equipped room |
| `hallway` | Corridor junction/waypoint |
| `exit` | Emergency exit (evacuation target) |
| `stairwell` | Vertical floor transition |

### Error Codes
| Code | Meaning |
|------|---------|
| 200 | OK |
| 404 | Building ID not found |

---

## `POST /api/inject?buildingId=...`

Inject fire, sensor failure, or communication failure.

### Purpose
Injects a hazard event at a specific node. Supports three scenario types: fire events (`slow_smolder`, `flashover`), sensor failures, and communication failures. If a demo is running, it is cancelled.

### Request Body
```json
{
    "nodeId": "n-zone-1",
    "scenario": "flashover"
}
```

### Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `nodeId` | `string` | Yes | Target node ID |
| `scenario` | `string` | Yes | Scenario type |

### Scenario Types
| Scenario | Effect |
|----------|--------|
| `slow_smolder` | Adds fire origin with slow logistic growth (0.05/tick) |
| `flashover` | Adds fire origin with fast growth (0.35/tick) |
| `sensor_failure` | Disables the sensor at the target node |
| `comm_failure` | Disables communication at the target node |

### Response
```json
{"ok": true}
```

### Error Codes
| Code | Meaning |
|------|---------|
| 200 | OK |
| 404 | Building or node not found |
| 422 | Invalid request body (missing fields) |

### Notes
- Injecting a fire scenario replaces the demo scenario
- Multiple fire origins can be active simultaneously
- Sensor failures set the node's `failoverTier` to `tertiary` and `sensorOk` to `false`

---

## `POST /api/reset?buildingId=...`

Reset simulation state.

### Purpose
Clears all fire origins, disabled sensors, disabled comms, hazard grids, and packet counters for the specified building. Also clears the snapshot replay buffer and cancels any running demo.

### Request Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `buildingId` | `string` | No | `mega-mall` | Building identifier |

### Request Body
None.

### Response
```json
{"ok": true}
```

### Error Codes
| Code | Meaning |
|------|---------|
| 200 | OK |

### Notes
- Resets are instant and not reversible
- The replay history is cleared along with the simulation state

---

## `POST /api/demo?buildingId=...`

Run automated 30-second demo sequence.

### Purpose
Resets the simulation and runs a pre-programmed multi-stage scenario injection sequence:

| Time | Event |
|------|-------|
| t+0s | Reset (start) |
| t+2s | Inject `slow_smolder` at one sensor node |
| t+5s | Inject `slow_smolder` at another sensor node |
| t+10s | Inject `flashover` at a sensor node |
| t+15s | Inject `comm_failure` at three sensor nodes |
| t+20s | Inject `sensor_failure` at two sensor nodes |

### Request Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `buildingId` | `string` | No | `mega-mall` | Building identifier |

### Request Body
None.

### Response
```json
{"ok": true}
```

### Error Codes
| Code | Meaning |
|------|---------|
| 200 | OK |
| 409 | Demo already running |

### Notes
- Calling demo again cancels any running demo and starts fresh
- The demo auto-targets sensor nodes on floors above ground level
- If the building has no suitable sensor nodes, no injection occurs

---

## `GET /api/replay?fromMs=...&toMs=...&buildingId=...`

Historical snapshot replay.

### Purpose
Returns all snapshots within a time window from the ring buffer (max 600 snapshots per building). Used for timeline scrubbing in the frontend.

### Request Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `fromMs` | `int` | No | `0` | Start timestamp (epoch ms) |
| `toMs` | `int` | No | current time | End timestamp (epoch ms) |
| `buildingId` | `string` | No | `mega-mall` | Building identifier |

### Response
```json
[
    {
        "t": 1712345678000,
        "status": "EVACUATION_ACTIVE",
        "scenario": "flashover",
        "nodes": {
            "n-zone-1": {
                "nodeId": "n-zone-1",
                "online": true,
                "temperature": 245.3,
                "smoke": 0.87,
                "co": 740.0,
                "flameDetected": true,
                "occupants": 12,
                "nextHop": "j-corridor-a-0",
                "failoverTier": "secondary",
                "lastSeenMs": 1712345678000,
                "sensorOk": true
            }
        },
        "hazard": {"0": [0.0, 0.12, 0.34, ...]},
        "routes": [
            {"id": "route-n-zone-1", "path": ["n-zone-1", "exit-north"], "priority": 0.85}
        ],
        "network": {
            "totalPackets": 1523,
            "packetsPerSec": 45,
            "crcFailures": 3,
            "staleNodes": 1,
            "avgLatencyMs": 14.5,
            "websocket": "connected"
        },
        "activeFireNodes": ["n-zone-1"]
    }
]
```

### Snapshot Fields
| Field | Type | Description |
|-------|------|-------------|
| `t` | `int` | Snapshot timestamp (epoch ms) |
| `status` | `string` | System status string |
| `scenario` | `string` | Active scenario name |
| `nodes` | `object` | Map of nodeId → NodeState |
| `hazard` | `object` | Map of floor index → 32×22 hazard grid array |
| `routes` | `array` | Evacuation route list |
| `network` | `object` | Network statistics |
| `activeFireNodes` | `array` | List of node IDs with detected fire |

### Status Values
| Status | Meaning |
|--------|---------|
| `NORMAL` | No hazards detected |
| `FIRE_DETECTED` | Smoke or temperature threshold exceeded |
| `EVACUATION_ACTIVE` | Flame detected, evacuation routing active |
| `SHELTER_IN_PLACE` | >6 fire nodes or >4 isolated nodes |
| `NO_SAFE_EXIT` | All exits blocked by fire |

### Error Codes
| Code | Meaning |
|------|---------|
| 200 | OK |
| 400 | Invalid time range parameters |

### Notes
- Maximum 600 snapshots in the buffer (120 seconds at 200ms intervals)
- Snapshots outside the requested range are filtered server-side

---

## `WS /api/events?buildingId=...`

Real-time WebSocket event stream.

### Purpose
Opens a persistent connection that receives snapshot pushes every 200ms. Also accepts injection commands from the client.

### Query Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `buildingId` | `string` | No | `mega-mall` | Building to subscribe to |

### Server → Client Messages
JSON snapshot objects (same structure as replay response items) pushed at 200ms intervals. On connection, the latest snapshot is sent immediately.

### Client → Server Messages
```json
{"inject": {"nodeId": "n-zone-1", "scenario": "flashover"}}
```

Injection messages are processed immediately and affect the building simulation on subsequent ticks.

### Error Codes
| Code | Meaning |
|------|---------|
| 101 | WebSocket upgrade successful |
| 400 | Invalid building ID |
| 1000 | Normal closure |

### Notes
- Each building has its own WebSocket connection pool
- Dead connections are cleaned lazily during tick broadcasts
- One client can subscribe to only one building per connection
- To monitor multiple buildings, open separate WebSocket connections
