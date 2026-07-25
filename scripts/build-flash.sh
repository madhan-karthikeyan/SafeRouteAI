#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../firmware"

echo "=== Building firmware ==="
pio run --environment esp32dev

if [ "${1:-}" = "flash" ]; then
    echo "=== Flashing ==="
    pio run --environment esp32dev -t upload
fi

echo "=== Done ==="
