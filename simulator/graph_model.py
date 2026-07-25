import json
from typing import List, Optional

class NodeConfig:
    def __init__(self, node_id: int, floor: int, x: float, y: float,
                 is_exit: bool = False, T_baseline: float = 25.0,
                 T_critical: float = 80.0, S_baseline: float = 0.0,
                 S_critical: float = 1000.0, occupant_capacity: float = 10.0):
        self.node_id = node_id
        self.floor = floor
        self.x = x
        self.y = y
        self.is_exit = is_exit
        self.T_baseline = T_baseline
        self.T_critical = T_critical
        self.S_baseline = S_baseline
        self.S_critical = S_critical
        self.occupant_capacity = occupant_capacity

class EdgeConfig:
    def __init__(self, from_id: int, to_id: int, base_distance: float,
                 occupant_capacity: float = 5.0, floor_transition: bool = False):
        self.from_id = from_id
        self.to_id = to_id
        self.base_distance = base_distance
        self.occupant_capacity = occupant_capacity
        self.floor_transition = floor_transition

class BuildingGraph:
    def __init__(self):
        self.nodes: List[NodeConfig] = []
        self.edges: List[EdgeConfig] = []

    def add_node(self, node: NodeConfig):
        self.nodes.append(node)

    def add_edge(self, edge: EdgeConfig):
        self.edges.append(edge)

    def find_node(self, node_id: int) -> Optional[NodeConfig]:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        return None

    def to_dict(self) -> dict:
        return {
            "nodes": [
                {
                    "id": n.node_id, "floor": n.floor, "x": n.x, "y": n.y,
                    "is_exit": n.is_exit, "T_baseline": n.T_baseline,
                    "T_critical": n.T_critical, "S_baseline": n.S_baseline,
                    "S_critical": n.S_critical,
                    "occupant_capacity": n.occupant_capacity
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "from": e.from_id, "to": e.to_id,
                    "base_distance": e.base_distance,
                    "occupant_capacity": e.occupant_capacity,
                    "floor_transition": e.floor_transition
                }
                for e in self.edges
            ]
        }

    @staticmethod
    def from_dict(data: dict) -> "BuildingGraph":
        g = BuildingGraph()
        for nd in data.get("nodes", []):
            g.add_node(NodeConfig(
                node_id=nd["id"], floor=nd.get("floor", 0),
                x=nd.get("x", 0), y=nd.get("y", 0),
                is_exit=nd.get("is_exit", False),
                T_baseline=nd.get("T_baseline", 25.0),
                T_critical=nd.get("T_critical", 80.0),
                S_baseline=nd.get("S_baseline", 0.0),
                S_critical=nd.get("S_critical", 1000.0),
                occupant_capacity=nd.get("occupant_capacity", 10.0)
            ))
        for ed in data.get("edges", []):
            g.add_edge(EdgeConfig(
                from_id=ed["from"], to_id=ed["to"],
                base_distance=ed["base_distance"],
                occupant_capacity=ed.get("occupant_capacity", 5.0),
                floor_transition=ed.get("floor_transition", False)
            ))
        return g

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @staticmethod
    def load(path: str) -> "BuildingGraph":
        with open(path) as f:
            return BuildingGraph.from_dict(json.load(f))

    def build_default(self):
        self.add_node(NodeConfig(1, 0, 0, 0, is_exit=True))
        self.add_node(NodeConfig(2, 0, 10, 0))
        self.add_node(NodeConfig(3, 0, 20, 5))
        self.add_node(NodeConfig(4, 0, 10, 10, is_exit=True))
        self.add_node(NodeConfig(5, 0, 0, 10))
        self.add_node(NodeConfig(6, 0, 20, -5, is_exit=True))

        self.add_edge(EdgeConfig(1, 2, 10.0, occupant_capacity=5))
        self.add_edge(EdgeConfig(2, 3, 12.0, occupant_capacity=5))
        self.add_edge(EdgeConfig(3, 6, 10.0, occupant_capacity=5))
        self.add_edge(EdgeConfig(2, 4, 14.0, occupant_capacity=8))
        self.add_edge(EdgeConfig(4, 5, 10.0, occupant_capacity=5))
        self.add_edge(EdgeConfig(5, 1, 10.0, occupant_capacity=5))
        self.add_edge(EdgeConfig(5, 2, 8.0, occupant_capacity=5))
        self.add_edge(EdgeConfig(3, 4, 6.0, occupant_capacity=3))
        return self
