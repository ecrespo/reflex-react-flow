"""T-009 / T-010 — event spec wiring (API Spec §3.1, Tech Design DD-002/DD-003).

Covers REQ-005 to REQ-014: every handler must filter its payload in JS *before*
the value is serialized into a Reflex event, so unfiltered React Flow objects
never reach the WebSocket (Constitution Art. 6).
"""

from __future__ import annotations

import pytest
import reflex as rx
from reflex_react_flow import react_flow


class Harness(rx.State):
    """Event handlers with the payload shapes the API Spec promises."""

    @rx.event
    def on_changes(self, changes: list[dict]) -> None:
        """Accept a change-delta list."""

    @rx.event
    def on_mapping(self, payload: dict) -> None:
        """Accept a single filtered object."""

    @rx.event
    def on_ids(self, ids: list[str]) -> None:
        """Accept a list of element ids."""


# event prop -> (bound handler, the JS filter it must call)
EVENT_FILTERS = {
    "on_nodes_change": (Harness.on_changes, "rrfFilterNodeChanges"),
    "on_edges_change": (Harness.on_changes, "rrfFilterEdgeChanges"),
    "on_connect": (Harness.on_mapping, "rrfFilterConnection"),
    "on_connect_start": (Harness.on_mapping, "rrfFilterConnectStart"),
    "on_connect_end": (Harness.on_mapping, "rrfFilterConnectEnd"),
    "on_node_click": (Harness.on_mapping, "rrfFilterNode"),
    "on_node_double_click": (Harness.on_mapping, "rrfFilterNode"),
    "on_node_drag_start": (Harness.on_mapping, "rrfFilterNodeDrag"),
    "on_node_drag_stop": (Harness.on_mapping, "rrfFilterNodeDrag"),
    "on_edge_click": (Harness.on_mapping, "rrfFilterEdge"),
    "on_pane_click": (Harness.on_mapping, "rrfFilterPaneClick"),
    "on_selection_change": (Harness.on_mapping, "rrfFilterSelection"),
    "on_nodes_delete": (Harness.on_ids, "rrfFilterDeleted"),
    "on_edges_delete": (Harness.on_ids, "rrfFilterDeleted"),
    "on_viewport_change": (Harness.on_mapping, "rrfFilterViewport"),
}

# API Spec §3.1 lists exactly these handlers.
EXPECTED_EVENT_COUNT = 15


def rendered_prop(component: rx.Component, react_name: str) -> str:
    """Return the rendered JS for one React prop."""
    for prop in component.render()["props"]:
        text = str(prop)
        if text.startswith(f"{react_name}:"):
            return text
    raise AssertionError(f"{react_name} was not rendered; got {component.render()['props']}")


def to_camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(word.capitalize() for word in rest)


# --------------------------------------------------------------------------
# REQ-005..014 — every handler filters in JS
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("event_prop", "spec"), sorted(EVENT_FILTERS.items()))
def test_handler_filters_payload_in_js(event_prop: str, spec: tuple) -> None:
    """REQ-005..014: the payload is passed through its filter, not sent raw."""
    handler, expected_filter = spec
    component = react_flow(**{event_prop: handler})

    rendered = rendered_prop(component, to_camel(event_prop))
    assert expected_filter in rendered, f"{event_prop} must call {expected_filter}"


def test_every_spec_event_is_supported() -> None:
    """Art. 5: the API Spec §3.1 event list ships whole, not partially."""
    assert len(EVENT_FILTERS) == EXPECTED_EVENT_COUNT

    declared = react_flow().get_event_triggers()
    for event_prop in EVENT_FILTERS:
        assert event_prop in declared, f"{event_prop} is not a declared event trigger"


def test_selection_change_sends_id_lists_only() -> None:
    """REQ-010: selection reports `{node_ids, edge_ids}` — never the elements."""
    rendered = rendered_prop(
        react_flow(on_selection_change=Harness.on_mapping), "onSelectionChange"
    )
    assert "rrfFilterSelection" in rendered


def test_connect_start_and_end_payloads_are_minimal() -> None:
    """REQ-014: connect start carries handle identity; end carries success only."""
    component = react_flow(on_connect_start=Harness.on_mapping, on_connect_end=Harness.on_mapping)
    assert "rrfFilterConnectStart" in rendered_prop(component, "onConnectStart")
    assert "rrfFilterConnectEnd" in rendered_prop(component, "onConnectEnd")


def test_unbound_events_are_not_rendered() -> None:
    """An event the user did not wire must not appear on the React component."""
    rendered = " ".join(str(prop) for prop in react_flow().render()["props"])
    for event_prop in EVENT_FILTERS:
        assert to_camel(event_prop) not in rendered


# --------------------------------------------------------------------------
# REQ-013 — the payload cap is per-canvas
# --------------------------------------------------------------------------


def test_payload_cap_defaults_to_32_kb() -> None:
    """REQ-013: the default cap is 32 KB."""
    component = react_flow(on_nodes_change=Harness.on_changes)
    assert "32" in rendered_prop(component, "onNodesChange")


@pytest.mark.parametrize("cap", [8, 64])
def test_payload_cap_is_configurable_per_canvas(cap: int) -> None:
    """REQ-013: `max_event_payload_kb` reaches the JS filter."""
    component = react_flow(on_nodes_change=Harness.on_changes, max_event_payload_kb=cap)
    assert f", {cap})" in rendered_prop(component, "onNodesChange")


def test_two_canvases_can_use_different_caps() -> None:
    """REQ-013: the cap is per-instance, not a module-wide constant."""
    small = react_flow(on_nodes_change=Harness.on_changes, max_event_payload_kb=8)
    large = react_flow(on_nodes_change=Harness.on_changes, max_event_payload_kb=64)

    assert ", 8)" in rendered_prop(small, "onNodesChange")
    assert ", 64)" in rendered_prop(large, "onNodesChange")


# --------------------------------------------------------------------------
# REQ-012 — viewport debounce
# --------------------------------------------------------------------------


def test_viewport_change_is_debounced() -> None:
    """REQ-012: the viewport handler is wrapped in the keyed debounce."""
    component = react_flow(on_viewport_change=Harness.on_mapping)
    rendered = rendered_prop(component, "onViewportChange")

    assert "rrfDebounceKeyed" in rendered
    assert "200" in rendered, "default debounce interval is 200 ms"


def test_viewport_debounce_interval_is_configurable() -> None:
    """REQ-012: `viewport_debounce_ms` is honoured."""
    component = react_flow(on_viewport_change=Harness.on_mapping, viewport_debounce_ms=50)
    assert "50" in rendered_prop(component, "onViewportChange")


def test_each_canvas_gets_its_own_debounce_key() -> None:
    """REQ-012: two canvases must not share one debounce timer."""
    first = rendered_prop(react_flow(on_viewport_change=Harness.on_mapping), "onViewportChange")
    second = rendered_prop(react_flow(on_viewport_change=Harness.on_mapping), "onViewportChange")

    def debounce_key(rendered: str) -> str:
        marker = 'rrfDebounceKeyed("'
        start = rendered.index(marker) + len(marker)
        return rendered[start : rendered.index('"', start)]

    assert debounce_key(first) != debounce_key(second)


def test_drag_events_are_not_debounced() -> None:
    """REQ-009: drag start/stop are discrete, so they must fire immediately."""
    component = react_flow(
        on_node_drag_start=Harness.on_mapping,
        on_node_drag_stop=Harness.on_mapping,
    )
    for react_name in ("onNodeDragStart", "onNodeDragStop"):
        assert "rrfDebounceKeyed" not in rendered_prop(component, react_name)


# --------------------------------------------------------------------------
# asset wiring (DD-004)
# --------------------------------------------------------------------------


@pytest.fixture
def app_assets_dir(tmp_path, monkeypatch):
    """Minimal Reflex app context.

    `rx.asset(shared=True)` symlinks into the host app's `assets/` directory, which
    only exists while an app compiles. The fixture supplies one so the asset wiring
    is covered here rather than deferred wholesale to the browser suite.
    """
    (tmp_path / "assets").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_filters_are_imported_from_the_shared_asset(app_assets_dir) -> None:
    """DD-004: the helpers ship as a packaged asset, not inlined JS strings."""
    custom_code = " ".join(react_flow(on_connect=Harness.on_mapping)._get_all_custom_code())

    assert "event_utils" in custom_code
    assert "rrfFilterConnection" in custom_code
    assert "import {" in custom_code, "helpers must be imported, not inlined"


def test_asset_is_symlinked_into_the_app(app_assets_dir) -> None:
    """DD-004: the JS actually lands in the app's external assets tree."""
    react_flow(on_connect=Harness.on_mapping)._get_all_custom_code()

    served = list((app_assets_dir / "assets" / "external").rglob("event_utils.js"))
    assert served, "event_utils.js was not published into the app assets"
    assert "rrfFilterNodeChanges" in served[0].read_text()
