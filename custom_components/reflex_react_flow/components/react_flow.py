"""The main canvas wrapper (API Spec §3.1).

This module is the only place where the Python surface meets React naming
(Constitution Art. 4, Tech Design §5.2 "Boundary translation"). Reflex camelises
prop names natively (Tech Design §12, finding S-01), so the wrapper does not
re-implement that translation; :data:`PROP_NAME_MAP` records the resulting contract
so it is asserted by tests and can be published as the parity table (Art. 5).
"""

from __future__ import annotations

from typing import Any

import reflex as rx
from reflex.vars.base import Var

__all__ = ["PROP_NAME_MAP", "ReactFlowLib", "react_flow"]

#: npm range for the wrapped library. The caret resolves to >=12.3.5 <13, which
#: satisfies the pin required by Tech Design §9 (finding S-02).
XYFLOW_PACKAGE = "@xyflow/react@^12.3.5"

#: The v12 stylesheet. Injected by the component so a canvas renders styled with
#: no user-added CSS (REQ-001).
XYFLOW_STYLESHEET = "@xyflow/react/dist/style.css"


def _to_camel(name: str) -> str:
    """Translate a snake_case prop name to the React prop name."""
    head, *rest = name.split("_")
    return head + "".join(word[:1].upper() + word[1:] for word in rest)


#: Props that configure *our* event specs rather than the React component. They are
#: read by the wrapper and must never be forwarded to `<ReactFlow>` (REQ-012/013).
WRAPPER_ONLY_PROPS: tuple[str, ...] = ("viewport_debounce_ms", "max_event_payload_kb")

_CANVAS_PROPS: tuple[str, ...] = (
    "nodes",
    "edges",
    "node_types",
    "edge_types",
    "color_mode",
    "fit_view",
    "default_edge_options",
    "connection_mode",
    "snap_to_grid",
    "snap_grid",
    "min_zoom",
    "max_zoom",
    "translate_extent",
    "node_extent",
    "nodes_draggable",
    "nodes_connectable",
    "nodes_focusable",
    "edges_focusable",
    "elements_selectable",
    "pan_on_drag",
    "zoom_on_scroll",
    "delete_key_code",
    "viewport",
    "default_viewport",
)

#: The API Spec §3.1 parity contract: Python prop -> React prop.
PROP_NAME_MAP: dict[str, str] = {name: _to_camel(name) for name in _CANVAS_PROPS}


class ReactFlowLib(rx.NoSSRComponent):
    """The `<ReactFlow>` canvas.

    Wrapped as a :class:`reflex.NoSSRComponent` (Tech Design DD-001): the canvas needs
    a measured DOM and `window`, so server prerendering buys nothing here and costs
    hydration bugs.
    """

    library = XYFLOW_PACKAGE
    tag = "ReactFlow"
    is_default = False  # v12 ships named exports (REQ-001)

    # --- graph content (REQ-002) ---
    nodes: Var[list[dict[str, Any]]]
    edges: Var[list[dict[str, Any]]]

    # --- type registries (REQ-020 / REQ-025) ---
    node_types: Var[dict[str, Any]]
    edge_types: Var[dict[str, Any]]

    # --- appearance and interaction (REQ-003, REQ-018) ---
    color_mode: Var[str]
    fit_view: Var[bool]
    default_edge_options: Var[dict[str, Any]]
    connection_mode: Var[str]
    snap_to_grid: Var[bool]
    snap_grid: Var[list[int]]
    min_zoom: Var[float]
    max_zoom: Var[float]
    translate_extent: Var[list[list[float]]]
    node_extent: Var[list[list[float]]]
    nodes_draggable: Var[bool]
    nodes_connectable: Var[bool]
    nodes_focusable: Var[bool]
    edges_focusable: Var[bool]
    elements_selectable: Var[bool]
    pan_on_drag: Var[bool]
    zoom_on_scroll: Var[bool]
    delete_key_code: Var[str | list[str] | None]
    viewport: Var[dict[str, float]]
    default_viewport: Var[dict[str, float]]

    def add_custom_code(self) -> list[str]:
        """Import the v12 stylesheet so the canvas renders styled (REQ-001)."""
        return [f'import "{XYFLOW_STYLESHEET}";']


def react_flow(*children: rx.Component, **props: Any) -> rx.Component:
    """Create a React Flow canvas.

    Args:
        *children: Plugin components (``background``, ``controls``, ``mini_map``,
            ``panel``, ...) and any ``panel`` content.
        **props: Canvas props from API Spec §3.1, in snake_case.

    Returns:
        The canvas component, ready to place in a Reflex page.

    Example:
        ```python
        rxf.react_flow(
            rxf.background(variant="dots"),
            rxf.controls(),
            nodes=State.nodes,
            edges=State.edges,
            fit_view=True,
        )
        ```
    """
    # Wrapper-level knobs never reach React; they parameterise the event specs.
    for wrapper_prop in WRAPPER_ONLY_PROPS:
        props.pop(wrapper_prop, None)

    return ReactFlowLib.create(*children, **props)
