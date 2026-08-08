"""T-007 — plugin component tests (API Spec §3.2, REQ-004)."""

from __future__ import annotations

import pytest
import reflex as rx
from reflex_react_flow.components.plugins import (
    background,
    controls,
    mini_map,
    node_resizer,
    node_toolbar,
    panel,
)
from reflex_react_flow.components.react_flow import XYFLOW_PACKAGE, react_flow

# API Spec §3.2: constructor -> the React component it must wrap.
PLUGIN_TAGS = {
    background: "Background",
    controls: "Controls",
    mini_map: "MiniMap",
    panel: "Panel",
    node_toolbar: "NodeToolbar",
    node_resizer: "NodeResizer",
}

PANEL_POSITIONS = (
    "top-left",
    "top-center",
    "top-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
)


def _rendered_props(component: rx.Component) -> str:
    return " ".join(str(prop) for prop in component.render()["props"])


@pytest.mark.parametrize(("constructor", "tag"), sorted(PLUGIN_TAGS.items(), key=lambda i: i[1]))
def test_plugin_wraps_expected_component(constructor, tag: str) -> None:
    """REQ-004: each constructor renders its named v12 component."""
    assert constructor().render()["name"] == tag


@pytest.mark.parametrize(("constructor", "tag"), sorted(PLUGIN_TAGS.items(), key=lambda i: i[1]))
def test_plugin_uses_named_import_from_xyflow(constructor, tag: str) -> None:
    """REQ-001/004: plugins come from @xyflow/react as named imports."""
    component = constructor()
    assert component.library == XYFLOW_PACKAGE
    assert component.is_default is False


# --- per-component prop surfaces (API Spec §3.2) --------------------------


@pytest.mark.parametrize("variant", ["dots", "lines", "cross"])
def test_background_variants(variant: str) -> None:
    """REQ-004: background supports the three v12 variants."""
    assert variant in _rendered_props(background(variant=variant))


def test_background_props_camelise() -> None:
    """REQ-003/004: gap, size and color reach React."""
    rendered = _rendered_props(background(variant="lines", gap=24, size=2, color="#ccc"))
    for expected in ("variant", "gap", "size", "color", "24", "2", "#ccc"):
        assert expected in rendered


def test_controls_toggles_camelise() -> None:
    """REQ-004: show_* toggles map to showZoom / showFitView / showInteractive."""
    rendered = _rendered_props(
        controls(show_zoom=False, show_fit_view=False, show_interactive=True)
    )
    assert "showZoom" in rendered
    assert "showFitView" in rendered
    assert "showInteractive" in rendered
    assert "show_zoom" not in rendered


def test_mini_map_props_camelise() -> None:
    """REQ-004: node_color maps to nodeColor."""
    rendered = _rendered_props(mini_map(pannable=True, zoomable=True, node_color="#abc"))
    assert "nodeColor" in rendered
    assert "pannable" in rendered
    assert "zoomable" in rendered
    assert "node_color" not in rendered


@pytest.mark.parametrize("position", PANEL_POSITIONS)
def test_panel_accepts_every_v12_position(position: str) -> None:
    """REQ-004: the v12 panel position enum is fully supported."""
    assert position in _rendered_props(panel(position=position))


def test_panel_renders_children() -> None:
    """REQ-004: panel is a container — its children render inside it.

    Verified in the T-005 spike: Reflex needs no slot wrapper here.
    """
    component = panel(rx.text("hello"), position="top-right")
    assert len(component.children) == 1


def test_node_toolbar_props_camelise() -> None:
    """REQ-004: is_visible maps to isVisible; offset passes through."""
    rendered = _rendered_props(node_toolbar(rx.text("x"), is_visible=True, offset=12))
    assert "isVisible" in rendered
    assert "offset" in rendered
    assert "is_visible" not in rendered


def test_node_resizer_props_camelise() -> None:
    """REQ-004: min_width/min_height map to minWidth/minHeight."""
    rendered = _rendered_props(node_resizer(min_width=40, min_height=30, color="#0f0"))
    assert "minWidth" in rendered
    assert "minHeight" in rendered
    assert "min_width" not in rendered


# --- composition (REQ-004) ------------------------------------------------


def test_all_plugins_compose_as_canvas_children() -> None:
    """REQ-004: the six plugins compose as children of react_flow."""
    canvas = react_flow(
        background(variant="dots"),
        controls(),
        mini_map(),
        panel(rx.text("legend"), position="top-left"),
        node_toolbar(rx.text("tools")),
        node_resizer(),
    )
    assert len(canvas.children) == len(PLUGIN_TAGS)

    rendered_children = {child.render()["name"] for child in canvas.children}
    assert rendered_children == set(PLUGIN_TAGS.values())
