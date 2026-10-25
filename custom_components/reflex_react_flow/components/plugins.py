"""Plugin components composable as children of the canvas (API Spec §3.2, REQ-004).

All six wrap named exports of the same npm package, so the library coordinates are
declared once on :class:`_XYFlowPlugin` rather than repeated per component
(Tech Design §5.2.1, DRY).
"""

from __future__ import annotations

from typing import Any

import reflex as rx
from reflex.vars.base import Var

from .react_flow import XYFLOW_PACKAGE

__all__ = [
    "background",
    "controls",
    "mini_map",
    "node_resizer",
    "node_toolbar",
    "panel",
]

#: The v12 panel position enum, shared by the positioned plugins.
PanelPosition = str


class _XYFlowPlugin(rx.Component):
    """Base for every plugin: same package, same named-import discipline."""

    library = XYFLOW_PACKAGE
    is_default = False


class Background(_XYFlowPlugin):
    """Canvas background pattern."""

    tag = "Background"

    variant: Var[str]
    gap: Var[int | list[int]]
    size: Var[float]
    color: Var[str]


class Controls(_XYFlowPlugin):
    """Zoom / fit-view / interactivity control panel."""

    tag = "Controls"

    show_zoom: Var[bool]
    show_fit_view: Var[bool]
    show_interactive: Var[bool]
    position: Var[PanelPosition]


class MiniMap(_XYFlowPlugin):
    """Overview map of the whole graph."""

    tag = "MiniMap"

    pannable: Var[bool]
    zoomable: Var[bool]
    node_color: Var[str]
    position: Var[PanelPosition]


class Panel(_XYFlowPlugin):
    """A positioned container floating over the canvas."""

    tag = "Panel"

    position: Var[PanelPosition]


class NodeToolbar(_XYFlowPlugin):
    """A toolbar anchored to a node."""

    tag = "NodeToolbar"

    is_visible: Var[bool]
    position: Var[str]
    offset: Var[float]


class NodeResizer(_XYFlowPlugin):
    """Resize handles for a node."""

    tag = "NodeResizer"

    min_width: Var[float]
    min_height: Var[float]
    is_visible: Var[bool]
    color: Var[str]


def background(**props: Any) -> rx.Component:
    """Create a canvas background.

    Args:
        **props: `variant` ("dots", "lines" or "cross"), `gap`, `size`, `color`.

    Returns:
        The background component.
    """
    return Background.create(**props)


def controls(**props: Any) -> rx.Component:
    """Create the zoom/fit-view control panel.

    Args:
        **props: `show_zoom`, `show_fit_view`, `show_interactive`, `position`.

    Returns:
        The controls component.
    """
    return Controls.create(**props)


def mini_map(**props: Any) -> rx.Component:
    """Create the minimap.

    Args:
        **props: `pannable`, `zoomable`, `node_color`, `position`.

    Returns:
        The minimap component.
    """
    return MiniMap.create(**props)


def panel(*children: rx.Component, **props: Any) -> rx.Component:
    """Create a floating panel over the canvas.

    Args:
        *children: The panel content — any Reflex components.
        **props: `position` from the v12 panel position enum.

    Returns:
        The panel component.
    """
    return Panel.create(*children, **props)


def node_toolbar(*children: rx.Component, **props: Any) -> rx.Component:
    """Create a toolbar anchored to a node.

    Args:
        *children: The toolbar content.
        **props: `is_visible`, `position`, `offset`.

    Returns:
        The node toolbar component.
    """
    return NodeToolbar.create(*children, **props)


def node_resizer(**props: Any) -> rx.Component:
    """Create resize handles for a node.

    Args:
        **props: `min_width`, `min_height`, `is_visible`, `color`.

    Returns:
        The node resizer component.
    """
    return NodeResizer.create(**props)
