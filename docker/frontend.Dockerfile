FROM oven/bun:1.2-slim AS builder

WORKDIR /app

COPY frontend/package.json frontend/bun.lock* ./
RUN bun install

COPY frontend/ .

ENV VITE_API_BASE=http://localhost:8000
ENV VITE_WS_URL=ws://localhost:8000/api/events
ENV VITE_USE_MOCK=false

EXPOSE 5173

CMD ["bun", "run", "dev", "--host", "0.0.0.0", "--port", "5173"]
