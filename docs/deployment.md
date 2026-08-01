# SafeRouteAI — Deployment Guide

## Production Architecture

```
                      ┌─────────────────┐
                      │   DNS / CDN     │
                      │ (Cloudflare)    │
                      └────────┬────────┘
                               │
                      ┌────────▼────────┐
                      │  Reverse Proxy  │
                      │    nginx:80     │
                      │    nginx:443    │
                      └───┬────────┬────┘
                          │        │
              ┌───────────▼─┐  ┌──▼───────────┐
              │  Frontend   │  │   Backend     │
              │  Static     │  │  uvicorn x4   │
              │  (Vite)     │  │  :8000        │
              └─────────────┘  └───┬───────────┘
                                    │
                           ┌───────▼───────┐
                           │   Mosquitto   │
                           │   MQTT :1883  │
                           └───────┬───────┘
                                   │
                           ┌───────▼───────┐
                           │   ESP32 Mesh  │
                           │  (N nodes)    │
                           └───────────────┘
```

---

## Docker Compose (Production)

```yaml
# docker-compose.prod.yml
services:
  mosquitto:
    image: eclipse-mosquitto:2
    container_name: evac-mqtt
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./docker/mosquitto/mosquitto.prod.conf:/mosquitto/config/mosquitto.conf:z
      - mosquitto-data:/mosquitto/data
      - mosquitto-log:/mosquitto/log
    restart: always

  backend:
    build:
      context: .
      dockerfile: docker/backend.Dockerfile
    container_name: evac-backend
    ports:
      - "8000:8000"
    environment:
      - MQTT_BROKER=mosquitto
      - MQTT_PORT=1883
      - UVICORN_WORKERS=4
      - LOG_LEVEL=info
    depends_on:
      - mosquitto
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 15s
      timeout: 5s
      retries: 3

  frontend:
    build:
      context: .
      dockerfile: docker/frontend.Dockerfile
    container_name: evac-frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_BASE=http://localhost:8000
      - VITE_WS_URL=ws://localhost:8000/api/events
      - VITE_USE_MOCK=false
    depends_on:
      - backend
    restart: always

  nodered:
    image: nodered/node-red:latest
    container_name: evac-dashboard
    ports:
      - "1880:1880"
    volumes:
      - ./dashboard:/data:z
    depends_on:
      - mosquitto
    restart: always

volumes:
  mosquitto-data:
  mosquitto-log:
```

Start with:

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## Environment Variable Configuration (Production)

### Backend

| Variable | Production Value | Notes |
|---|---|---|
| `MQTT_BROKER` | `mosquitto` (container) or external IP | Use TLS for external connections |
| `MQTT_PORT` | `8883` (TLS) or `1883` (internal) | Prefer encrypted port |
| `UVICORN_WORKERS` | `4` | Match to CPU cores |
| `LOG_LEVEL` | `warning` | Reduce verbosity |

### Frontend

| Variable | Production Value | Notes |
|---|---|---|
| `VITE_USE_MOCK` | `false` | Always false in production |
| `VITE_API_BASE` | `https://api.yourdomain.com` | Public backend URL |
| `VITE_WS_URL` | `wss://api.yourdomain.com/api/events` | WSS for secure WebSocket |

### Mosquitto

| Variable | Production Value | Notes |
|---|---|---|
| `allow_anonymous` | `false` | Require authentication |
| `listener` | `8883` (TLS), `1883` (internal) | Separate ports |
| `cafile` | `/etc/mosquitto/certs/ca.crt` | CA certificate path |
| `certfile` | `/etc/mosquitto/certs/server.crt` | Server certificate |
| `keyfile` | `/etc/mosquitto/certs/server.key` | Server private key |

---

## MQTT Broker Security

### 1. Create certificates

```bash
# CA key + cert
openssl req -new -x509 -days 3650 -extensions v3_ca \
  -keyout ca.key -out ca.crt -subj "/CN=SafeRouteAI CA"

# Server key + CSR + cert
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=evac-mqtt"
openssl x509 -req -days 365 -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt

# Client key + CSR + cert (one per ESP32)
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr -subj "/CN=esp32-01"
openssl x509 -req -days 365 -in client.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out client.crt
```

### 2. Mosquitto config (`mosquitto.prod.conf`)

```
listener 1883 localhost
protocol mqtt

listener 8883
protocol mqtt
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
require_certificate true
tls_version tlsv1.2

listener 9001
protocol websockets
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key

allow_anonymous false
password_file /etc/mosquitto/passwd
acl_file /etc/mosquitto/acl

# Persistence
persistence true
persistence_location /mosquitto/data/
log_dest file /mosquitto/log/mosquitto.log
```

### 3. Create MQTT credentials

```bash
docker exec evac-mqtt mosquitto_passwd -c /mosquitto/passwd sensor-node-01
docker exec evac-mqtt mosquitto_passwd /mosquitto/passwd backend-service
```

---

## Backend Scaling

The backend is a stateless FastAPI application. Scale via uvicorn workers:

```bash
# Direct
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4

# Docker Compose (scale backend service)
docker-compose -f docker-compose.prod.yml up -d --scale backend=4
```

Each worker runs the `_tick_loop` independently. The simulation state (`SimState`) is in-process memory, so scaling requires sticky sessions or moving state to Redis. For multi-instance scaling, a Redis-backed SnapshotStore should replace the in-memory ring buffer.

---

## Frontend Static Build

```bash
cd frontend
VITE_USE_MOCK=false \
VITE_API_BASE=https://api.yourdomain.com \
VITE_WS_URL=wss://api.yourdomain.com/api/events \
bun run build
```

The build output is in `frontend/dist/`. Serve with nginx as static files.

---

## Reverse Proxy Setup (nginx)

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # Frontend static files
    root /var/www/saferouteai/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_buffering off;

        # WebSocket support
        location /api/events {
            proxy_pass http://127.0.0.1:8000/api/events;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_read_timeout 86400s;
        }
    }

    # Node-RED dashboard
    location /dashboard/ {
        proxy_pass http://127.0.0.1:1880/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; connect-src 'self' ws: wss:; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:;" always;
}
```

---

## Health Checks & Monitoring

### Backend health endpoint

```http
GET /api/health
Response: {
  "status": "ok",
  "buildings": 3,
  "ws_connections": 5,
  "tick_running": true
}
```

### Prometheus metrics (recommended)

Add `prometheus-fastapi-instrumentator` to `backend/requirements.txt` and instrument:

```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

### Alert thresholds

| Metric | Warning | Critical |
|---|---|---|
| Backend health check | 3 failures | 5 failures |
| WebSocket connections | 0 for 30s | 0 for 60s |
| CRC failure rate | > 5% | > 15% |
| Stale nodes | > 30% | > 60% |
| Disk usage | > 80% | > 90% |
| Memory usage | > 75% | > 90% |
| CPU load (15m avg) | > 2.0 | > 4.0 |

---

## Backup & Restore

### What to back up

| Component | Location | Frequency |
|---|---|---|
| Building definitions | `frontend/src/assets/buildings/` | On change |
| MQTT passwords | `docker/mosquitto/passwd` | On change |
| TLS certificates | `/etc/mosquitto/certs/` | On renewal |
| Node-RED flows | `dashboard/` directory | Daily |
| Docker volumes | `mosquitto-data`, `mosquitto-log` | Daily |
| Compose files | `docker-compose*.yml` + `.env` | On change |

### Backup script

```bash
#!/usr/bin/env bash
BACKUP_DIR="/backups/saferouteai/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Docker volumes
docker run --rm -v mosquitto-data:/data -v "$BACKUP_DIR:/backup" \
  alpine tar czf /backup/mosquitto-data.tar.gz -C /data .

# Configuration
cp docker-compose*.yml "$BACKUP_DIR/"
cp docker/mosquitto/*.conf "$BACKUP_DIR/"
cp docker/mosquitto/passwd "$BACKUP_DIR/" 2>/dev/null || true

# TLS certs
cp -r /etc/mosquitto/certs "$BACKUP_DIR/" 2>/dev/null || true

# Building assets
cp -r frontend/src/assets/buildings "$BACKUP_DIR/"

# Node-RED flows
cp -r dashboard/* "$BACKUP_DIR/dashboard/" 2>/dev/null || true

echo "Backup complete: $BACKUP_DIR"
```

### Restore

```bash
docker compose down
# Restore volumes from tarball
docker run --rm -v mosquitto-data:/data -v /path/to/backup:/backup \
  alpine tar xzf /backup/mosquitto-data.tar.gz -C /data
# Restart stack
docker compose up -d
```

---

## Network Security Considerations

| Concern | Mitigation |
|---|---|
| MQTT unencrypted | Use TLS on port 8883; disable anonymous access |
| Backend exposed | Listen only on `127.0.0.1` behind reverse proxy; never expose raw `:8000` |
| ESP32 authentication | Client certificates per device; MQTT username/password |
| WebSocket hijacking | Validate `Origin` header in nginx; use WSS |
| DDoS on MQTT | Rate-limit connections per IP in nginx; Mosquitto `max_connections` |
| Secrets in source | Use `.env` files (gitignored) or Docker secrets; never commit secrets |
| Software updates | Subscribe to security advisories for: ESP-IDF, Mosquitto, Python, Node.js |
| Firewall | Allow only ports 80, 443, (optional 1880 for dashboard). Drop all others |
| Backend CORS | Restrict `allow_origins` to your domain; remove wildcard in production |
| Logging | Centralize logs (Loki, ELK); retain 30 days; rotate daily |
| Intrusion detection | Fail2ban on nginx; monitor `/api/health`; alert on abnormal CRC rates |

---

## Recommended Hosting

| Provider | Spec | Estimated Cost | Notes |
|---|---|---|---|
| VPS (DigitalOcean, Linode, Hetzner) | 4 vCPU, 8 GB RAM, 80 GB SSD | ~$40-80/mo | Sufficient for 50+ ESP32 nodes |
| VPS (low-end) | 2 vCPU, 4 GB RAM, 50 GB SSD | ~$15-30/mo | Adequate for testing / pilot |
| Cloud (AWS ECS / GCP Cloud Run) | Autoscaling | Variable | Better for multi-region deployments |
| On-premise (Raspberry Pi 4/5) | 4 GB RAM | $50-100 one-time | Suitable for a single-building deployment |

### Minimum VPS requirements

- **OS**: Ubuntu 22.04 or 24.04 LTS
- **Docker**: 24+ with Compose v2
- **CPU**: 2 cores × 2.0 GHz
- **RAM**: 4 GB
- **Disk**: 30 GB SSD
- **Network**: 1 Gbps, static public IP
