"""
Building loader — reads building definitions from JSON files
in the assets/buildings/ directory. Mirrors the frontend's buildingService.ts.
"""

import json
import os
from .models import BuildingDef, BuildingMeta

BUILDINGS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "src", "assets", "buildings"
)

_cache: dict[str, BuildingDef] = {}
_index: list[BuildingMeta] | None = None


def _load_index() -> list[BuildingMeta]:
    global _index
    if _index is not None:
        return _index
    path = os.path.join(BUILDINGS_DIR, "index.json")
    with open(path) as f:
        data = json.load(f)
    _index = [BuildingMeta(**b) for b in data["buildings"]]
    return _index


def get_available_buildings() -> list[BuildingMeta]:
    return _load_index()


def get_building_meta(building_id: str) -> BuildingMeta | None:
    for b in _load_index():
        if b.id == building_id:
            return b
    return None


def load_building_def(building_id: str) -> BuildingDef:
    if building_id in _cache:
        return _cache[building_id]

    path = os.path.join(BUILDINGS_DIR, building_id, "building.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Building '{building_id}' not found at {path}")

    with open(path) as f:
        raw = json.load(f)

    def_ = BuildingDef(**raw)
    _cache[building_id] = def_
    return def_
