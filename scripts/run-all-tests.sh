#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "============================================"
echo "  SafeRouteAI - Running All Tests"
echo "============================================"

failed=0

echo ""
echo "=== Firmware Tests ==="
for t in tests/firmware/*.py; do
    echo "  Running $(basename "$t")..."
    if python3 "$t"; then
        echo "  PASS"
    else
        echo "  FAIL"
        failed=$((failed + 1))
    fi
    echo ""
done

echo "=== Simulator Tests ==="
for t in tests/simulator/*.py; do
    echo "  Running $(basename "$t")..."
    if python3 "$t"; then
        echo "  PASS"
    else
        echo "  FAIL"
        failed=$((failed + 1))
    fi
    echo ""
done

echo "=== Integration Tests ==="
if python3 tests/integration/test_scenarios.py; then
    echo "  PASS"
else
    echo "  FAIL"
    failed=$((failed + 1))
fi
echo ""

echo "============================================"
if [ $failed -eq 0 ]; then
    echo "  ALL TESTS PASSED"
else
    echo "  $failed TEST GROUPS FAILED"
fi
echo "============================================"
exit $failed
