"""The main canvas wrapper (API Spec §3.1).

This module is the only place where the Python surface meets React naming
(Constitution Art. 4, Tech Design §5.2 "Boundary translation"). Reflex camelises
prop names natively (Tech Design §12, finding S-01), so the wrapper does not
re-implement that translation; :data:`PROP_NAME_MAP` records the resulting contract
so it is asserted by tests and can be published as the parity table (Art. 5).

Two knobs — the payload cap and the viewport debounce interval — must be baked into
the *JavaScript* of the event specs, but Reflex resolves event triggers per class,
not per instance. :func:`_canvas_class` therefore mints (and memoises) one component
subclass per configuration, so two canvases on the same page can carry different
caps without sharing a class.
"""

from __future__ import annotations

import itertools
from functools import cache
from typing import Any

import reflex as rx
from reflex.vars.base import LiteralVar, Var

from ..assets import event_utils_path
from .events import EVENT_FILTER_NAMES, build_event_specs

__all__ = ["PROP_NAME_MAP", "ReactFlowLib", "react_flow"]

#: npm range for the wrapped library. The caret resolves to >=12.3.5 <13, which
#: satisfies the pin required by Tech Design §9 (finding S-02).
XYFLOW_PACKAGE = "@xyflow/react@^12.3.5"

#: The v12 stylesheet. Injected by the component so a canvas renders styled with
#: no user-added CSS (REQ-001).
XYFLOW_STYLESHEET = "@xyflow/react/dist/style.css"

#: Defaults from API Spec §3.1.
DEFAULT_VIEWPORT_DEBOUNCE_MS = 200
DEFAULT_MAX_EVENT_PAYLOAD_KB = 32

#: Distinguishes canvases so their debounce timers stay independent (REQ-012).
_canvas_counter = itertools.count(1)

#: Props whose array identity React Flow tracks. A literal value would be rebuilt
#: on every render, so the wrapper hoists it to a module-level constant.
_HOISTED_PROPS: tuple[str, ...] = ("nodes", "edges")


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


def _asset_import() -> str:
    """Build the import statement for the packaged event helpers (DD-004).

    Resolved lazily: ``rx.asset`` symlinks into the *app's* assets directory, which
    only exists once a Reflex app is compiling. Calling it at module import time
    would make the package unimportable outside an app.
    """
    path = event_utils_path()
    names = ", ".join(EVENT_FILTER_NAMES)
    return f'import {{ {names} }} from "$/public{path}";'


class ReactFlowLib(rx.NoSSRComponent):
    """The `<ReactFlow>` canvas.

    Wrapped as a :class:`reflex.NoSSRComponent` (Tech Design DD-001): the canvas needs
    a measured DOM and `window`, so server prerendering buys nothing here and costs
    hydration bugs.
    """

    library = XYFLOW_PACKAGE
    tag = "ReactFlow"
    is_default = False  # v12 ships named exports (REQ-001)

    #: Debounce token for this canvas; set by :func:`_canvas_class` (REQ-012).
    _debounce_key: str = ""
    _viewport_debounce_ms: int = DEFAULT_VIEWPORT_DEBOUNCE_MS
    #: JS constant name -> literal value, for the static props hoisted by
    #: :func:`react_flow`.
    _hoisted_literals: dict[str, Var] = {}  # noqa: RUF012 - replaced per instance

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
        """Inject the v12 stylesheet, the event helpers and any hoisted literals."""
        # `!s`: formatting a Var directly would embed Reflex's `<reflex.Var>` marker,
        # which is only resolved inside rendered props, not in raw module code.
        hoisted = [f"const {name} = {value!s};" for name, value in self._hoisted_literals.items()]
        return [f'import "{XYFLOW_STYLESHEET}";', _asset_import(), *hoisted]

    def _render(self, props: dict[str, Any] | None = None):
        """Wrap the viewport and selection handlers (REQ-010, REQ-012, DD-003).

        A debounce or a dedupe has to wrap the whole callback, which an argument
        spec cannot express — specs only transform arguments. The wrapping
        therefore happens here, on the rendered event chain, and only for the
        events whose specs call for it: the viewport is debounced, and a
        selection is sent only when it actually changed.
        """
        tag = super()._render(props)
        chain = tag.props.get("onViewportChange")
        if chain is not None:
            handler_js = str(Var.create(chain))
            tag.props["onViewportChange"] = Var(
                f'((v) => rrfDebounceKeyed("{self._debounce_key}", '
                f"() => ({handler_js})(v), {self._viewport_debounce_ms}))"
            )
        chain = tag.props.get("onSelectionChange")
        if chain is not None:
            handler_js = str(Var.create(chain))
            tag.props["onSelectionChange"] = Var(
                f'((p) => rrfDedupeKeyed("{self._debounce_key}:selection", '
                f"rrfFilterSelection(p), () => ({handler_js})(p)))"
            )
        return tag


@cache
def _canvas_class(max_payload_kb: int) -> type[ReactFlowLib]:
    """Return the canvas subclass whose event specs carry `max_payload_kb`.

    Memoised so repeated canvases with the same cap share one class — the cache is
    bounded in practice because it is keyed only by the cap, of which an app uses a
    handful at most.
    """
    specs = build_event_specs(max_payload_kb)
    namespace: dict[str, Any] = {
        "__module__": __name__,
        "__doc__": f"ReactFlow canvas with a {max_payload_kb} KB event payload cap.",
        "__annotations__": {
            event_prop: rx.EventHandler[spec] for event_prop, spec in specs.items()
        },
    }
    return type(f"ReactFlowLib{max_payload_kb}KB", (ReactFlowLib,), namespace)


def _static_literal(value: Any) -> Var | None:
    """Return `value` as a Var when it is a literal with no state dependency.

    A Python list counts only if nothing inside it references state: a hoisted
    constant lives at module scope, where state Vars are not in scope.
    """
    var = Var.create(value)
    if isinstance(var, LiteralVar) and var._get_all_var_data() is None:
        return var
    return None


def _hoist_static_props(props: dict[str, Any], canvas_id: int) -> dict[str, Var]:
    """Replace literal ``nodes``/``edges`` with references to module-level constants.

    React Flow treats a new ``nodes`` array as new nodes: it re-measures them and
    re-fires ``onNodesChange`` and ``onSelectionChange``. An inline literal is
    rebuilt on every render, and the state update those events trigger is itself
    a render — a feedback loop that floods the socket (Art. 6). A constant
    declared once per page keeps the identity stable across renders.

    Returns:
        JS constant name -> literal value, for :meth:`ReactFlowLib.add_custom_code`.
    """
    hoisted: dict[str, Var] = {}
    for prop in _HOISTED_PROPS:
        if prop not in props or (literal := _static_literal(props[prop])) is None:
            continue
        name = f"rrf_canvas_{canvas_id}_{prop}"
        hoisted[name] = literal
        props[prop] = Var(name, _var_type=list[dict[str, Any]])
    return hoisted


def react_flow(*children: rx.Component, **props: Any) -> rx.Component:
    """Create a React Flow canvas.

    Args:
        *children: Plugin components (``background``, ``controls``, ``mini_map``,
            ``panel``, ...) and any ``panel`` content.
        **props: Canvas props from API Spec §3.1, in snake_case, plus the event
            handlers and the two wrapper-level knobs ``viewport_debounce_ms``
            (default 200) and ``max_event_payload_kb`` (default 32).

    Returns:
        The canvas component, ready to place in a Reflex page.

    Example:
        ```python
        rxf.react_flow(
            rxf.background(variant="dots"),
            rxf.controls(),
            nodes=State.nodes,
            edges=State.edges,
            on_nodes_change=State.handle_nodes_change,
            fit_view=True,
        )
        ```
    """
    # Wrapper-level knobs never reach React; they parameterise the event specs.
    debounce_ms = props.pop("viewport_debounce_ms", DEFAULT_VIEWPORT_DEBOUNCE_MS)
    max_payload_kb = props.pop("max_event_payload_kb", DEFAULT_MAX_EVENT_PAYLOAD_KB)

    canvas_id = next(_canvas_counter)
    hoisted = _hoist_static_props(props, canvas_id)

    component = _canvas_class(max_payload_kb).create(*children, **props)
    component._debounce_key = f"rrf-canvas-{canvas_id}"
    component._hoisted_literals = hoisted
    component._viewport_debounce_ms = debounce_ms
    return component
