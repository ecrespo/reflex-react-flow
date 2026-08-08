"""T-011 — demo app tests.

The demo is the integration target and the living documentation, so it must at
minimum compile: every page renders, every Phase-1 event is wired, and the
`data-testid` hooks the Playwright suite addresses are present.

These are render-level assertions, not browser assertions — the browser evidence
is T-012's job.
"""

from __future__ import annotations

import pytest
from flow_demo.state import EDGE_TYPE_EDGES, SUBFLOW_NODES

from flow_demo.flow_demo import debug_panel, edge_types, index, subflows

PAGES = {"index": index, "edge_types": edge_types, "subflows": subflows, "debug": debug_panel}

# Every Layer 1 event from API Spec §3.1 must be exercised by the demo.
PHASE_1_EVENTS = (
    "on_nodes_change",
    "on_edges_change",
    "on_connect",
    "on_connect_start",
    "on_connect_end",
    "on_node_click",
    "on_node_double_click",
    "on_edge_click",
    "on_pane_click",
    "on_node_drag_start",
    "on_node_drag_stop",
    "on_selection_change",
    "on_nodes_delete",
    "on_edges_delete",
    "on_viewport_change",
)


def render_text(page) -> str:
    """Render a page to its serialized component tree."""
    return str(page().render())


@pytest.mark.parametrize("name", sorted(PAGES))
def test_page_renders(name: str) -> None:
    """Every demo page compiles to a component tree."""
    assert render_text(PAGES[name])


@pytest.mark.parametrize("name", sorted(PAGES))
def test_page_mounts_a_canvas_with_plugins(name: str) -> None:
    """REQ-002/004: each page shows a canvas with the plugin components."""
    rendered = render_text(PAGES[name])

    assert "ReactFlow" in rendered
    for plugin in ("Background", "Controls", "MiniMap", "Panel"):
        assert plugin in rendered, f"{name} is missing {plugin}"


@pytest.mark.parametrize("event", PHASE_1_EVENTS)
def test_demo_wires_every_phase_1_event(event: str) -> None:
    """Art. 5: the demo exercises the whole Phase-1 event surface, not a subset."""
    head, *rest = event.split("_")
    react_name = head + "".join(word.capitalize() for word in rest)
    assert react_name in render_text(index)


@pytest.mark.parametrize("testid", ["canvas", "color-mode-toggle"])
def test_playwright_hooks_are_present(testid: str) -> None:
    """T-012 addresses elements by data-testid, not by React Flow internals."""
    assert testid in render_text(index)


def test_debug_panel_exposes_the_event_ledger() -> None:
    """REQ-009/012/013: the budget assertions need observable counters."""
    rendered = render_text(debug_panel)

    for testid in ("event-counts", "last-payload", "last-payload-bytes", "reset-counts"):
        assert testid in rendered


def test_edge_types_page_covers_every_edge_type() -> None:
    """REQ-017: one edge of each of the four types, with labels."""
    declared = {edge["type"] for edge in EDGE_TYPE_EDGES}
    assert declared == {"bezier", "step", "smoothstep", "straight"}

    assert all(edge.get("label") for edge in EDGE_TYPE_EDGES)
    assert any("markerEnd" in edge for edge in EDGE_TYPE_EDGES)
    assert any("markerStart" in edge for edge in EDGE_TYPE_EDGES)


def test_subflow_children_declare_parent_and_extent() -> None:
    """REQ-015: children name their parent and clamp to it."""
    children = [node for node in SUBFLOW_NODES if node.get("parentId")]

    assert children, "the subflow page must contain nested nodes"
    for child in children:
        assert child["extent"] == "parent"

    parent_ids = {child["parentId"] for child in children}
    node_ids = {node["id"] for node in SUBFLOW_NODES}
    assert parent_ids <= node_ids, "every parent_id must reference a declared node"

    # v12 ordering rule (Data Model §2.1): parents precede their children.
    order = [node["id"] for node in SUBFLOW_NODES]
    for child in children:
        assert order.index(child["parentId"]) < order.index(child["id"])


def test_color_mode_is_state_bound_and_toggleable() -> None:
    """REQ-018: colour mode comes from state and a control flips it.

    Whether the canvas actually repaints without a reload is a browser fact, so
    that half of REQ-018 belongs to T-012; what is checkable here is that the
    prop is bound to state rather than hard-coded, and that a handler exists.
    """
    rendered = render_text(index)

    assert "colorMode" in rendered
    assert "color_mode" in rendered, "the prop must track state, not a literal"
    assert "toggle_color_mode" in rendered
