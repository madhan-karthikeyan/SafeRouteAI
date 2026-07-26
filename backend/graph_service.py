"""
Building graph loader — serves building metadata and graphs
by delegating to the building_loader and node_placer modules.
Supports multiple building definitions loaded from JSON.
"""

from .building_loader import get_available_buildings, get_building_meta, load_building_def
from .node_placer import place_nodes
from .models import BuildingGraph, BuildingMeta


def list_buildings() -> list[BuildingMeta]:
    return get_available_buildings()


def load_graph(building_id: str | None = None) -> BuildingGraph:
    bid = building_id or "mega-mall"
    def_ = load_building_def(bid)
    return place_nodes(def_)


def get_string_id(numeric_id: int, graph: BuildingGraph | None = None) -> str | None:
    """Map numeric ESP32 node ID to string ID using node list index."""
    if graph is None:
        graph = load_graph()
    if 0 <= numeric_id < len(graph.nodes):
        return graph.nodes[numeric_id].id
    return None


def get_numeric_id(string_id: str, graph: BuildingGraph | None = None) -> int | None:
    """Map string node ID to numeric ESP32 ID using node list index."""
    if graph is None:
        graph = load_graph()
    for i, n in enumerate(graph.nodes):
        if n.id == string_id:
            return i
    return None
