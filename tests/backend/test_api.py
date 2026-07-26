#!/usr/bin/env python3

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

PASS = 0
FAIL = 0


def check(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}")


def test_get_buildings():
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.get("/api/buildings")
    check("GET /api/buildings returns 200", resp.status_code == 200)
    data = resp.json()
    check("returns a list", isinstance(data, list))
    if data:
        check("first item has id", "id" in data[0])
        check("first item has name", "name" in data[0])
        check("first item has type", "type" in data[0])
        check("first item has floors", "floors" in data[0])


def test_get_graph():
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.get("/api/graph")
    check("GET /api/graph returns 200", resp.status_code == 200)
    data = resp.json()
    check("has nodes list", "nodes" in data)
    check("has edges list", "edges" in data)
    check("has floors list", "floors" in data)
    check("has hazardGrid", "hazardGrid" in data)
    check("nodes > 0", len(data["nodes"]) > 0)
    check("edges > 0", len(data["edges"]) > 0)
    check("node has id", "id" in data["nodes"][0])
    check("node has kind", "kind" in data["nodes"][0])
    check("edge has from", "from" in data["edges"][0])
    check("edge has to", "to" in data["edges"][0])


def test_get_graph_with_building_id():
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.get("/api/graph?buildingId=mega-mall")
    check("GET /api/graph?buildingId= returns 200", resp.status_code == 200)
    data = resp.json()
    check("requested building id matches", data.get("id") == "mega-mall")


def test_inject_and_reset():
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.post("/api/reset")
    check("POST /api/reset returns 200", resp.status_code == 200)

    resp = client.post("/api/inject", json={"nodeId": "n-atrium", "scenario": "flashover"})
    check("POST /api/inject returns 200", resp.status_code == 200)

    resp = client.post("/api/reset")
    check("POST /api/reset after inject returns 200", resp.status_code == 200)


def test_inject_invalid_scenario():
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.post("/api/inject", json={"nodeId": "n-atrium", "scenario": "invalid"})
    check("POST /api/inject with unknown scenario returns 200", resp.status_code == 200)


def test_health():
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.get("/api/health")
    check("GET /api/health returns 200", resp.status_code == 200)
    data = resp.json()
    check("health has status", data.get("status") == "ok")
    check("health has buildings count", isinstance(data.get("buildings"), int))
    check("health has ws_connections count", isinstance(data.get("ws_connections"), int))


def test_replay():
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.get("/api/replay")
    check("GET /api/replay returns 200", resp.status_code == 200)
    data = resp.json()
    check("replay returns a list", isinstance(data, list))


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            print(f"\n{name}:")
            fn()

    print(f"\n{'='*40}")
    print(f"Passed: {PASS}, Failed: {FAIL}")
    sys.exit(0 if FAIL == 0 else 1)
