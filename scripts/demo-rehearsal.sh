#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "====================================="
echo "  SafeRouteAI Demo Rehearsal Script"
echo "====================================="
echo ""

echo "=== 1. Running unit tests ==="
python3 -m pytest tests/firmware/ tests/simulator/ -v --tb=short 2>/dev/null || {
    echo "Running tests individually..."
    for t in tests/firmware/*.py tests/simulator/*.py; do
        echo "  - $t"
        python3 "$t" || true
    done
}
echo ""

echo "=== 2. Running integration tests ==="
python3 tests/integration/test_scenarios.py || true
echo ""

echo "=== 3. Testing injector packet generation ==="
python3 simulator/injector.py --zone 3 --profile flashover --packet 2
echo ""

echo "=== 4. Testing corrupt packet mode ==="
python3 simulator/injector.py --zone 3 --profile flashover --corrupt --packet 2
echo ""

echo "=== 5. Testing injector CLI (non-interactive) ==="
echo "zone 3" | python3 simulator/injector.py --cli 2>&1 || true
echo ""

echo "====================================="
echo "  Demo rehearsal complete."
echo "====================================="
