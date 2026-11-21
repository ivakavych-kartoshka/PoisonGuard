"""Typed acyclic lineage graph used by both persistent sinks."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict
from typing import Iterable

from poisonguard.data.schemas import LineageNode, NodeType


class LineageGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, LineageNode] = {}
        self.children: dict[str, set[str]] = {}
        self.parents: dict[str, set[str]] = {}

    def add_node(self, node: LineageNode) -> None:
        existing = self.nodes.get(node.node_id)
        if existing and asdict(existing) != asdict(node):
            raise ValueError(f"immutable node ID reused with different content: {node.node_id}")
        self.nodes.setdefault(node.node_id, node)
        self.children.setdefault(node.node_id, set())
        self.parents.setdefault(node.node_id, set())

    def add_edge(self, parent: str, child: str) -> None:
        if parent not in self.nodes or child not in self.nodes:
            raise KeyError("both lineage endpoints must exist")
        if parent == child or parent in self.descendants({child}):
            raise ValueError("edge would create a lineage cycle")
        self.children[parent].add(child)
        self.parents[child].add(parent)

    def descendants(self, roots: Iterable[str]) -> set[str]:
        roots = set(roots)
        missing = roots - self.nodes.keys()
        if missing:
            raise KeyError(f"unknown lineage roots: {sorted(missing)}")
        seen, queue = set(roots), deque(roots)
        while queue:
            current = queue.popleft()
            for child in self.children[current] - seen:
                seen.add(child)
                queue.append(child)
        return seen

    def ancestors(self, nodes: Iterable[str]) -> set[str]:
        nodes = set(nodes)
        missing = nodes - self.nodes.keys()
        if missing:
            raise KeyError(f"unknown lineage nodes: {sorted(missing)}")
        seen, queue = set(nodes), deque(nodes)
        while queue:
            current = queue.popleft()
            for parent in self.parents[current] - seen:
                seen.add(parent)
                queue.append(parent)
        return seen

    def source_closure(self, node_id: str) -> set[str]:
        return {item for item in self.ancestors({node_id})
                if self.nodes[item].node_type is NodeType.EVENT}

    def invalidate(self, roots: Iterable[str]) -> set[str]:
        affected = self.descendants(roots)
        for node_id in affected:
            self.nodes[node_id].valid = False
        return affected

    def validate_parent_completeness(self, node_id: str, expected: Iterable[str]) -> bool:
        return set(expected).issubset(self.parents.get(node_id, set()))

    def to_dict(self) -> dict[str, object]:
        return {
            "nodes": [
                {**asdict(n), "node_type": n.node_type.value}
                for n in sorted(self.nodes.values(), key=lambda x: (x.logical_time, x.node_id))
            ],
            "edges": sorted((a, b) for a, values in self.children.items() for b in values),
        }

    def counts(self, node_ids: Iterable[str] | None = None) -> dict[str, int]:
        selected = set(node_ids) if node_ids is not None else set(self.nodes)
        counts: dict[str, int] = {}
        for node_id in selected:
            key = self.nodes[node_id].node_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts
