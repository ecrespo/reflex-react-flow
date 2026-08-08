"""reflex-react-flow demo app — living documentation and integration target.

Every page is written the way a user would write it: pure Python, no JSX. The
`data-testid` hooks exist so the Playwright suite (T-012) can address elements
without depending on React Flow's internal class names.
"""

from __future__ import annotations

import reflex as rx
import reflex_react_flow as rxf

from .state import (
    EDGE_TYPE_EDGES,
    EDGE_TYPE_NODES,
    SUBFLOW_EDGES,
    SUBFLOW_NODES,
    DemoState,
)

CANVAS_STYLE = {"width": "100%", "height": "560px", "border": "1px solid #d0d7de"}

PAGES = [
    ("/", "Quickstart"),
    ("/edge-types", "Edge types"),
    ("/subflows", "Subflows"),
    ("/debug", "Debug panel"),
]


def nav() -> rx.Component:
    """Render the page navigation shared by every demo page."""
    return rx.hstack(
        *[
            rx.link(
                label,
                href=href,
                padding="0.25rem 0.75rem",
                custom_attrs={"data-testid": f"nav-{href}"},
            )
            for href, label in PAGES
        ],
        spacing="2",
        padding_y="0.75rem",
    )


def shell(title: str, description: str, *children: rx.Component) -> rx.Component:
    """Wrap a page in the common heading and navigation."""
    return rx.container(
        rx.vstack(
            rx.heading(title, size="7"),
            rx.text(description, color_scheme="gray"),
            nav(),
            *children,
            align_items="stretch",
            spacing="3",
            width="100%",
        ),
        max_width="1100px",
        padding="1.5rem",
    )


def canvas(nodes, edges, **overrides) -> rx.Component:
    """Build a canvas with the demo's standard plugins and full event wiring.

    Args:
        nodes: The nodes Var or list.
        edges: The edges Var or list.
        **overrides: Extra canvas props for the specific page.

    Returns:
        The configured canvas component.
    """
    props: dict = {
        "nodes": nodes,
        "edges": edges,
        "fit_view": True,
        "color_mode": DemoState.color_mode,
        "on_nodes_change": DemoState.on_nodes_change,
        "on_edges_change": DemoState.on_edges_change,
        "on_connect": DemoState.on_connect,
        "on_connect_start": DemoState.on_connect_start,
        "on_connect_end": DemoState.on_connect_end,
        "on_node_click": DemoState.on_node_click,
        "on_node_double_click": DemoState.on_node_double_click,
        "on_edge_click": DemoState.on_edge_click,
        "on_pane_click": DemoState.on_pane_click,
        "on_node_drag_start": DemoState.on_node_drag_start,
        "on_node_drag_stop": DemoState.on_node_drag_stop,
        "on_selection_change": DemoState.on_selection_change,
        "on_nodes_delete": DemoState.on_nodes_delete,
        "on_edges_delete": DemoState.on_edges_delete,
        "on_viewport_change": DemoState.on_viewport_change,
        "custom_attrs": {"data-testid": "canvas"},
        "style": CANVAS_STYLE,
    }
    props.update(overrides)

    return rxf.react_flow(
        rxf.background(variant="dots", gap=18),
        rxf.controls(),
        rxf.mini_map(pannable=True, zoomable=True),
        rxf.panel(color_mode_toggle(), position="top-right"),
        **props,
    )


def color_mode_toggle() -> rx.Component:
    """REQ-018: flip the canvas between light and dark without a reload."""
    return rx.button(
        rx.cond(DemoState.color_mode == "light", "Dark mode", "Light mode"),
        on_click=DemoState.toggle_color_mode,
        size="1",
        custom_attrs={"data-testid": "color-mode-toggle"},
    )


def index() -> rx.Component:
    """Quickstart: a three-node pipeline rendered from Python dicts (REQ-002)."""
    return shell(
        "Quickstart",
        "A three-node pipeline declared in pure Python — drag, connect and delete.",
        canvas(DemoState.nodes, DemoState.edges),
        rx.text(
            "Events received: ",
            rx.text.strong(DemoState.event_counts.to_string()),
            custom_attrs={"data-testid": "event-counts"},
            size="2",
        ),
    )


def edge_types() -> rx.Component:
    """REQ-017: one edge of each type, with labels and markers."""
    return shell(
        "Edge types",
        "bezier, step, smoothstep and straight — plus labels, markers and animation.",
        canvas(EDGE_TYPE_NODES, EDGE_TYPE_EDGES),
    )


def subflows() -> rx.Component:
    """REQ-015: a group container whose children are clamped to its bounds."""
    return shell(
        "Subflows",
        "Children declare parent_id and extent='parent'; dragging clamps to the parent.",
        canvas(SUBFLOW_NODES, SUBFLOW_EDGES),
    )


def debug_panel() -> rx.Component:
    """Event ledger backing the REQ-009/REQ-012/REQ-013 budget assertions."""
    return shell(
        "Debug panel",
        "Live event counts and payload sizes — the evidence for the event-channel budgets.",
        rx.hstack(
            rx.button(
                "Reset counters",
                on_click=DemoState.reset_counts,
                custom_attrs={"data-testid": "reset-counts"},
            ),
            spacing="2",
        ),
        rx.box(
            rx.text("Counts", weight="bold", size="2"),
            rx.text(
                DemoState.event_counts.to_string(),
                custom_attrs={"data-testid": "event-counts"},
                size="2",
                font_family="monospace",
            ),
            rx.text("Last payload", weight="bold", size="2", margin_top="0.5rem"),
            rx.text(
                DemoState.last_payload,
                custom_attrs={"data-testid": "last-payload"},
                size="2",
                font_family="monospace",
                white_space="pre-wrap",
            ),
            rx.text(
                "Last payload bytes: ",
                DemoState.last_payload_bytes.to_string(),
                custom_attrs={"data-testid": "last-payload-bytes"},
                size="2",
            ),
            padding="0.75rem",
            border="1px solid #d0d7de",
            border_radius="6px",
        ),
        canvas(DemoState.nodes, DemoState.edges),
    )


app = rx.App()
app.add_page(index, route="/", title="reflex-react-flow — Quickstart")
app.add_page(edge_types, route="/edge-types", title="reflex-react-flow — Edge types")
app.add_page(subflows, route="/subflows", title="reflex-react-flow — Subflows")
app.add_page(debug_panel, route="/debug", title="reflex-react-flow — Debug panel")
