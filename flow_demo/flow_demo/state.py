"""Demo state.

Layer 3 (`FlowState`, Phase 3) does not exist yet, so the demo wires the Layer 1
events onto a plain `rx.State`. That is deliberate: it proves the wrapper is
usable on its own, without the high-level helpers.

The event counters exist for the Playwright budget assertions in T-012 — REQ-012
("pan for 1 s produces <= 6 events") and REQ-009 ("a drag produces exactly one
start and one stop") are only checkable if the app reports what it received.
"""

from __future__ import annotations

import json

import reflex as rx

QUICKSTART_NODES: list[dict] = [
    {
        "id": "1",
        "type": "input",
        "position": {"x": 0, "y": 80},
        "data": {"label": "Extract"},
    },
    {
        "id": "2",
        "position": {"x": 220, "y": 80},
        "data": {"label": "Transform"},
    },
    {
        "id": "3",
        "type": "output",
        "position": {"x": 440, "y": 80},
        "data": {"label": "Load"},
    },
]

QUICKSTART_EDGES: list[dict] = [
    {"id": "e1-2", "source": "1", "target": "2", "animated": True},
    {"id": "e2-3", "source": "2", "target": "3"},
]

# REQ-017: one edge of every type, plus labels and markers.
EDGE_TYPE_NODES: list[dict] = [
    {
        "id": f"n{i}",
        "position": {"x": 0 if i % 2 == 0 else 320, "y": 40 + (i // 2) * 110},
        "data": {"label": f"n{i}"},
    }
    for i in range(8)
]

EDGE_TYPE_EDGES: list[dict] = [
    {
        "id": "e-bezier",
        "source": "n0",
        "target": "n1",
        "type": "bezier",
        "label": "bezier",
        "markerEnd": {"type": "arrowclosed"},
    },
    {
        "id": "e-step",
        "source": "n2",
        "target": "n3",
        "type": "step",
        "label": "step",
        "markerEnd": {"type": "arrow"},
    },
    {
        "id": "e-smoothstep",
        "source": "n4",
        "target": "n5",
        "type": "smoothstep",
        "label": "smoothstep",
        "markerStart": {"type": "arrow"},
    },
    {
        "id": "e-straight",
        "source": "n6",
        "target": "n7",
        "type": "straight",
        "label": "straight",
        "animated": True,
    },
]

# REQ-015: a group container with children clamped to its bounds.
SUBFLOW_NODES: list[dict] = [
    {
        "id": "group-1",
        "type": "group",
        "position": {"x": 40, "y": 40},
        "data": {"label": "Pipeline"},
        "width": 340,
        "height": 220,
    },
    {
        "id": "child-a",
        "position": {"x": 30, "y": 60},
        "data": {"label": "child A"},
        "parentId": "group-1",
        "extent": "parent",
    },
    {
        "id": "child-b",
        "position": {"x": 180, "y": 130},
        "data": {"label": "child B"},
        "parentId": "group-1",
        "extent": "parent",
    },
    {
        "id": "outside",
        "position": {"x": 440, "y": 120},
        "data": {"label": "outside"},
    },
]

SUBFLOW_EDGES: list[dict] = [
    {"id": "e-ab", "source": "child-a", "target": "child-b"},
    {"id": "e-b-out", "source": "child-b", "target": "outside"},
]


class DemoState(rx.State):
    """Graph state plus an event ledger for the integration budgets."""

    nodes: list[dict] = QUICKSTART_NODES
    edges: list[dict] = QUICKSTART_EDGES

    color_mode: str = "light"

    # --- event ledger (read by the debug panel and by Playwright) ---
    event_counts: dict[str, int] = {}

    #: Last payload *per event name*. Keyed rather than a single slot because
    #: React Flow interleaves events — a `dimensions` change lands right after a
    #: click and would otherwise overwrite the payload a test is asserting on.
    payloads: dict[str, str] = {}

    #: Append-only `event|payload` log, newest last, bounded.
    #: Keying by event name is still not enough for `on_nodes_change`, which
    #: carries several change *types*: a `dimensions` batch arrives right behind
    #: a `position` batch under the same name. A history lets an assertion find
    #: the batch it cares about instead of racing for the most recent one.
    payload_log: list[str] = []

    last_payload: str = ""
    last_payload_bytes: int = 0

    def _record(self, name: str, payload: object) -> None:
        """Record one received event for the debug panel."""
        counts = dict(self.event_counts)
        counts[name] = counts.get(name, 0) + 1
        self.event_counts = counts

        serialized = json.dumps(payload, separators=(",", ":"))
        self.payloads = {**self.payloads, name: serialized[:600]}
        self.payload_log = [*self.payload_log, f"{name}|{serialized[:600]}"][-40:]
        self.last_payload = f"{name}: {serialized[:400]}"
        self.last_payload_bytes = len(serialized.encode())

    @rx.event
    def reset_counts(self) -> None:
        """Clear the ledger so a test can measure one interaction in isolation."""
        self.event_counts = {}
        self.payloads = {}
        self.last_payload = ""
        self.last_payload_bytes = 0

    # --- Layer 1 event handlers -------------------------------------------

    @rx.event
    def on_nodes_change(self, changes: list[dict]) -> None:
        """Apply position/select deltas (REQ-005).

        A deliberately small subset of `apply_node_changes`: the full, tested
        implementation lands in Phase 3 (T-017) and the demo will switch to it.

        **Only writes back when a change actually applied.** Reassigning `nodes`
        unconditionally creates an infinite feedback loop: a new list is a new
        prop, React Flow re-measures the canvas, emits a `dimensions` change, and
        the handler fires again — observed at ~60 events/second, which would
        saturate exactly the channel Art. 6 protects. `apply_node_changes`
        (T-017) must preserve this no-op-when-nothing-changed property.
        """
        self._record("on_nodes_change", changes)

        by_id = {node["id"]: dict(node) for node in self.nodes}
        mutated = False
        for change in changes:
            node = by_id.get(change.get("id", ""))
            if node is None:
                continue
            if change["type"] == "position" and "position" in change:
                if node.get("position") != change["position"]:
                    node["position"] = change["position"]
                    mutated = True
            elif change["type"] == "select":
                selected = change.get("selected", False)
                if node.get("selected") != selected:
                    node["selected"] = selected
                    mutated = True

        if mutated:
            self.nodes = list(by_id.values())

    @rx.event
    def on_edges_change(self, changes: list[dict]) -> None:
        """Record edge deltas (REQ-006)."""
        self._record("on_edges_change", changes)

    @rx.event
    def on_connect(self, connection: dict) -> None:
        """Add the edge the user just drew (REQ-007)."""
        self._record("on_connect", connection)
        source, target = connection.get("source"), connection.get("target")
        if not source or not target:
            return
        self.edges = [
            *self.edges,
            {"id": f"e{source}-{target}-{len(self.edges)}", "source": source, "target": target},
        ]

    @rx.event
    def on_connect_start(self, payload: dict) -> None:
        """Record a connection gesture starting (REQ-014)."""
        self._record("on_connect_start", payload)

    @rx.event
    def on_connect_end(self, payload: dict) -> None:
        """Record a connection gesture ending (REQ-014)."""
        self._record("on_connect_end", payload)

    @rx.event
    def on_node_click(self, payload: dict) -> None:
        """Record a node click (REQ-008)."""
        self._record("on_node_click", payload)

    @rx.event
    def on_node_double_click(self, payload: dict) -> None:
        """Record a node double click (REQ-008)."""
        self._record("on_node_double_click", payload)

    @rx.event
    def on_edge_click(self, payload: dict) -> None:
        """Record an edge click (REQ-008)."""
        self._record("on_edge_click", payload)

    @rx.event
    def on_pane_click(self, payload: dict) -> None:
        """Record a pane click (REQ-008)."""
        self._record("on_pane_click", payload)

    @rx.event
    def on_node_drag_start(self, payload: dict) -> None:
        """Record a drag starting (REQ-009)."""
        self._record("on_node_drag_start", payload)

    @rx.event
    def on_node_drag_stop(self, payload: dict) -> None:
        """Record a drag stopping (REQ-009)."""
        self._record("on_node_drag_stop", payload)

    @rx.event
    def on_selection_change(self, payload: dict) -> None:
        """Record a selection change (REQ-010)."""
        self._record("on_selection_change", payload)

    @rx.event
    def on_nodes_delete(self, ids: list[str]) -> None:
        """Drop deleted nodes and their incident edges (REQ-011)."""
        self._record("on_nodes_delete", ids)
        removed = set(ids)
        self.nodes = [node for node in self.nodes if node["id"] not in removed]
        self.edges = [
            edge
            for edge in self.edges
            if edge["source"] not in removed and edge["target"] not in removed
        ]

    @rx.event
    def on_edges_delete(self, ids: list[str]) -> None:
        """Drop deleted edges (REQ-011)."""
        self._record("on_edges_delete", ids)
        removed = set(ids)
        self.edges = [edge for edge in self.edges if edge["id"] not in removed]

    @rx.event
    def on_viewport_change(self, viewport: dict) -> None:
        """Record a debounced viewport update (REQ-012)."""
        self._record("on_viewport_change", viewport)

    @rx.event
    def toggle_color_mode(self) -> None:
        """Flip the canvas colour mode (REQ-018)."""
        self.color_mode = "dark" if self.color_mode == "light" else "light"
