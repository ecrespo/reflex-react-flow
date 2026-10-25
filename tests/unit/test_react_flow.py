"""T-006 — canvas wrapper tests (API Spec §3.1).

Covers REQ-001 (v12 named imports + CSS injection), REQ-002 (nodes/edges render)
and REQ-003 (snake_case props reach React camelCased).
"""

from __future__ import annotations

import pytest
from reflex_react_flow.components.react_flow import PROP_NAME_MAP, ReactFlowLib, react_flow

# The API Spec §3.1 prop table, as an executable contract. Reflex camelises props
# natively (Tech Design §12, finding S-01); this table guards against a regression
# there and pins any prop whose React name is not the naive camelisation.
EXPECTED_PROP_NAMES = {
    "nodes": "nodes",
    "edges": "edges",
    "node_types": "nodeTypes",
    "edge_types": "edgeTypes",
    "color_mode": "colorMode",
    "fit_view": "fitView",
    "default_edge_options": "defaultEdgeOptions",
    "connection_mode": "connectionMode",
    "snap_to_grid": "snapToGrid",
    "snap_grid": "snapGrid",
    "min_zoom": "minZoom",
    "max_zoom": "maxZoom",
    "translate_extent": "translateExtent",
    "node_extent": "nodeExtent",
    "nodes_draggable": "nodesDraggable",
    "nodes_connectable": "nodesConnectable",
    "nodes_focusable": "nodesFocusable",
    "edges_focusable": "edgesFocusable",
    "elements_selectable": "elementsSelectable",
    "pan_on_drag": "panOnDrag",
    "zoom_on_scroll": "zoomOnScroll",
    "delete_key_code": "deleteKeyCode",
    "viewport": "viewport",
    "default_viewport": "defaultViewport",
}

# Wrapper-level knobs (API Spec §3.1): they configure our event specs and must
# never be forwarded to the React component, which would not understand them.
WRAPPER_ONLY_PROPS = ("viewport_debounce_ms", "max_event_payload_kb")


def _rendered_prop_names(component) -> set[str]:
    """Return the React prop names present on a rendered component."""
    return {str(prop).split(":", 1)[0] for prop in component.render()["props"]}


# --------------------------------------------------------------------------
# REQ-001 — v12 wrapping
# --------------------------------------------------------------------------


def test_targets_xyflow_react_v12() -> None:
    """REQ-001: the wrapper depends on @xyflow/react in the 12.x range."""
    assert ReactFlowLib.library is not None
    assert ReactFlowLib.library.startswith("@xyflow/react@")
    assert "12" in ReactFlowLib.library


def test_uses_named_import_not_default() -> None:
    """REQ-001: v12 exposes named exports; a default import would be wrong."""
    assert ReactFlowLib.is_default is False

    dynamic_imports = react_flow()._get_all_dynamic_imports()
    joined = " ".join(dynamic_imports)
    assert "mod.ReactFlow" in joined
    assert "mod.default" not in joined


def test_injects_stylesheet_without_user_action() -> None:
    """REQ-001: the v12 stylesheet is imported by the component itself."""
    custom_code = react_flow()._get_all_custom_code()
    assert any("@xyflow/react/dist/style.css" in code for code in custom_code)


def test_is_client_side_only() -> None:
    """DD-001: the canvas is wrapped as a NoSSR component."""
    import reflex as rx

    assert issubclass(ReactFlowLib, rx.NoSSRComponent)


# --------------------------------------------------------------------------
# REQ-003 — prop translation table
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("python_prop", "react_prop"), sorted(EXPECTED_PROP_NAMES.items()))
def test_every_spec_prop_is_declared(python_prop: str, react_prop: str) -> None:
    """REQ-003: every API Spec §3.1 prop exists and maps to its React name."""
    assert python_prop in ReactFlowLib.get_props(), f"{python_prop} is not a declared prop"
    assert PROP_NAME_MAP[python_prop] == react_prop


def test_props_reach_react_camel_cased() -> None:
    """REQ-003: a populated canvas renders every prop under its React name."""
    component = react_flow(
        nodes=[],
        edges=[],
        fit_view=True,
        snap_to_grid=True,
        snap_grid=[15, 15],
        min_zoom=0.5,
        max_zoom=2.0,
        nodes_draggable=False,
        elements_selectable=True,
        pan_on_drag=True,
        zoom_on_scroll=False,
        color_mode="dark",
        connection_mode="loose",
        delete_key_code="Backspace",
    )
    rendered = _rendered_prop_names(component)

    for python_prop in (
        "fit_view",
        "snap_to_grid",
        "snap_grid",
        "min_zoom",
        "max_zoom",
        "nodes_draggable",
        "elements_selectable",
        "pan_on_drag",
        "zoom_on_scroll",
        "color_mode",
        "connection_mode",
        "delete_key_code",
    ):
        assert EXPECTED_PROP_NAMES[python_prop] in rendered
        assert python_prop not in rendered, "snake_case must not leak to React (Art. 4)"


@pytest.mark.parametrize("wrapper_prop", WRAPPER_ONLY_PROPS)
def test_wrapper_only_props_do_not_leak_into_css(wrapper_prop: str) -> None:
    """REQ-012/013: debounce and payload-cap knobs configure our specs, not React.

    Reflex does not discard undeclared props — it absorbs them into the component's
    `css` object, so an unconsumed knob would ship as a bogus CSS declaration
    (`viewportDebounceMs: 99`). The wrapper must consume these before `create`.
    """
    component = react_flow(**{wrapper_prop: 99})
    rendered = " ".join(str(prop) for prop in component.render()["props"])

    assert wrapper_prop not in rendered
    assert _to_camel_for_test(wrapper_prop) not in rendered
    assert "99" not in rendered


def _to_camel_for_test(name: str) -> str:
    """Independent camelisation, so the test does not reuse the code under test."""
    head, *rest = name.split("_")
    return head + "".join(word.capitalize() for word in rest)


def test_prop_map_covers_exactly_the_spec_table() -> None:
    """REQ-003 / Art. 5: the prop map neither omits nor invents surface.

    Silent partial coverage must not ship, so the declared map is compared against
    the spec table as a set, not merely checked for containment.
    """
    assert set(PROP_NAME_MAP) - set(WRAPPER_ONLY_PROPS) == set(EXPECTED_PROP_NAMES)


# --------------------------------------------------------------------------
# REQ-002 — rendering nodes and edges
# --------------------------------------------------------------------------


def test_renders_nodes_and_edges() -> None:
    """REQ-002: declared nodes and edges are serialized onto the canvas."""
    component = react_flow(
        nodes=[{"id": "1", "position": {"x": 0, "y": 0}, "data": {}}],
        edges=[{"id": "e1", "source": "1", "target": "2"}],
    )
    props = " ".join(str(prop) for prop in component.render()["props"])
    code = " ".join(component._get_all_custom_code())

    assert "nodes" in props
    assert "edges" in props
    assert '"1"' in code, "literal content is serialized into the page module"
    assert "<reflex.Var>" not in code, "module code must be plain JavaScript"


def test_literal_nodes_and_edges_are_hoisted_to_constants() -> None:
    """REQ-002 / Art. 6: a literal list keeps one array identity across renders.

    React Flow re-measures a `nodes` array it has not seen before and re-fires
    onNodesChange/onSelectionChange; an inline literal is rebuilt on each render,
    which turns the resulting state update into an endless event loop.
    """
    component = react_flow(
        nodes=[{"id": "1", "position": {"x": 0, "y": 0}, "data": {}}],
        edges=[{"id": "e1", "source": "1", "target": "2"}],
    )
    props = " ".join(str(prop) for prop in component.render()["props"])
    code = list(component._get_all_custom_code())

    for prop in ("nodes", "edges"):
        constants = [line for line in code if line.startswith("const rrf_canvas_")]
        name = next(line.split()[1] for line in constants if line.split()[1].endswith(prop))
        assert f"{prop}:{name}" in props.replace(" ", "")


def test_state_backed_nodes_are_not_hoisted() -> None:
    """REQ-002: a state Var must stay reactive, so it is passed through as is."""
    import reflex as rx

    class GraphState(rx.State):
        nodes: list[dict] = []  # noqa: RUF012 - Reflex deep-copies state defaults

    component = react_flow(nodes=GraphState.nodes)
    props = " ".join(str(prop) for prop in component.render()["props"])

    assert "rrf_canvas_" not in props
    assert not any(
        line.startswith("const rrf_canvas_") for line in component._get_all_custom_code()
    )


def test_literal_embedding_state_is_not_hoisted() -> None:
    """REQ-002: a list that references state cannot move to module scope."""
    import reflex as rx

    class LabelState(rx.State):
        label: str = "start"

    component = react_flow(
        nodes=[{"id": "1", "position": {"x": 0, "y": 0}, "data": {"label": LabelState.label}}],
    )

    assert not any(
        line.startswith("const rrf_canvas_") for line in component._get_all_custom_code()
    )


def test_accepts_plugin_children() -> None:
    """REQ-004 (wrapper side): plugin components compose as children of the canvas."""
    import reflex as rx

    component = react_flow(rx.text("panel content"))
    assert len(component.children) == 1


def test_tag_is_react_flow() -> None:
    """REQ-001: the wrapped React component is ReactFlow."""
    assert ReactFlowLib.tag == "ReactFlow"
    assert react_flow().render()["name"] == "ReactFlow"
