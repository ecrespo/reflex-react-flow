"""Event specs: the JS-side payload filters wired onto the canvas.

Constitution Art. 6 makes the WebSocket the scarce resource, so every handler
declares a spec whose JavaScript projects the payload down to the fields listed
in Data Model §3 *before* Reflex serializes it (Tech Design DD-002).

The specs are produced by a factory rather than written out fifteen times: the
payload cap is a per-canvas value, so the spec closures must capture it
(Tech Design §5.2.1 — DRY, and OCP for adding a sixteenth event).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from reflex.vars.base import Var

__all__ = ["EVENT_FILTER_NAMES", "build_event_specs"]

#: Every helper the specs call, so the import statement is generated from one list.
EVENT_FILTER_NAMES: tuple[str, ...] = (
    "rrfDebounceKeyed",
    "rrfFilterConnectEnd",
    "rrfFilterConnectStart",
    "rrfFilterConnection",
    "rrfFilterDeleted",
    "rrfFilterEdge",
    "rrfFilterEdgeChanges",
    "rrfFilterNode",
    "rrfFilterNodeChanges",
    "rrfFilterNodeDrag",
    "rrfFilterPaneClick",
    "rrfFilterSelection",
    "rrfFilterViewport",
)


def build_event_specs(max_payload_kb: int) -> dict[str, Callable[..., Any]]:
    """Build the fifteen event arg-specs for one canvas configuration.

    Args:
        max_payload_kb: Per-canvas serialized payload cap in KB (REQ-013). It is
            baked into the change filters because the cap must be enforced in the
            browser, before the payload reaches the socket.

    Returns:
        Mapping of Python event prop name to its Reflex arg-spec function.
    """
    # --- change deltas, capped (REQ-005, REQ-006, REQ-013) ---

    def on_nodes_change(changes: Var[list[dict]]) -> tuple[Var[list[dict]]]:
        return (Var(f"rrfFilterNodeChanges({changes}, {max_payload_kb})", _var_type=list[dict]),)

    def on_edges_change(changes: Var[list[dict]]) -> tuple[Var[list[dict]]]:
        return (Var(f"rrfFilterEdgeChanges({changes}, {max_payload_kb})", _var_type=list[dict]),)

    # --- connection lifecycle (REQ-007, REQ-014) ---

    def on_connect(connection: Var[dict]) -> tuple[Var[dict]]:
        return (Var(f"rrfFilterConnection({connection})", _var_type=dict),)

    def on_connect_start(event: Var, params: Var[dict]) -> tuple[Var[dict]]:
        return (Var(f"rrfFilterConnectStart({event}, {params})", _var_type=dict),)

    def on_connect_end(event: Var, state: Var[dict]) -> tuple[Var[dict]]:
        return (Var(f"rrfFilterConnectEnd({event}, {state})", _var_type=dict),)

    # --- pointer events (REQ-008, REQ-009) ---

    def on_node_click(event: Var, node: Var[dict]) -> tuple[Var[dict]]:
        return (Var(f"rrfFilterNode({event}, {node})", _var_type=dict),)

    def on_node_drag(event: Var, node: Var[dict]) -> tuple[Var[dict]]:
        return (Var(f"rrfFilterNodeDrag({event}, {node})", _var_type=dict),)

    def on_edge_click(event: Var, edge: Var[dict]) -> tuple[Var[dict]]:
        return (Var(f"rrfFilterEdge({event}, {edge})", _var_type=dict),)

    def on_pane_click(event: Var) -> tuple[Var[dict]]:
        return (Var(f"rrfFilterPaneClick({event})", _var_type=dict),)

    # --- selection and deletion (REQ-010, REQ-011) ---

    def on_selection_change(params: Var[dict]) -> tuple[Var[dict]]:
        return (Var(f"rrfFilterSelection({params})", _var_type=dict),)

    def on_elements_delete(elements: Var[list[dict]]) -> tuple[Var[list[str]]]:
        return (Var(f"rrfFilterDeleted({elements})", _var_type=list[str]),)

    # --- viewport (REQ-012) ---

    def on_viewport_change(viewport: Var[dict]) -> tuple[Var[dict]]:
        return (Var(f"rrfFilterViewport({viewport})", _var_type=dict),)

    return {
        "on_nodes_change": on_nodes_change,
        "on_edges_change": on_edges_change,
        "on_connect": on_connect,
        "on_connect_start": on_connect_start,
        "on_connect_end": on_connect_end,
        "on_node_click": on_node_click,
        "on_node_double_click": on_node_click,
        "on_node_drag_start": on_node_drag,
        "on_node_drag_stop": on_node_drag,
        "on_edge_click": on_edge_click,
        "on_pane_click": on_pane_click,
        "on_selection_change": on_selection_change,
        "on_nodes_delete": on_elements_delete,
        "on_edges_delete": on_elements_delete,
        "on_viewport_change": on_viewport_change,
    }
