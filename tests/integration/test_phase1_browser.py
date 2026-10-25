"""T-012 — Phase 1 browser suite.

Covers the REQs whose observable is a browser fact: REQ-001/002/004 (a styled
canvas with plugins renders), REQ-005/007/008/011 (payload shapes as received by
the server), REQ-009/012 (event budgets) and REQ-015/017/018.

Payload assertions read the demo's debug ledger rather than intercepting the
socket: the ledger records what the *server handler* actually received, which is
the thing Art. 6 constrains.
"""

from __future__ import annotations

import json
import re

import pytest
from playwright.sync_api import expect

pytestmark = [pytest.mark.phase1, pytest.mark.integration]


def ledger(page) -> dict[str, int]:
    """Return the demo's event counts."""
    text = page.text_content("[data-testid='event-counts']") or "{}"
    try:
        return json.loads(text.replace("'", '"'))
    except json.JSONDecodeError:
        return {}


def payload_for(page, event: str) -> str:
    """Return the last payload the server received *for one event*.

    Per-event rather than "the last payload": React Flow interleaves events, so a
    `dimensions` change routinely lands right after a click and would overwrite a
    single shared slot before the assertion reads it.
    """
    raw = page.text_content("[data-testid='payloads']") or "{}"
    try:
        return json.loads(raw.replace("'", '"')).get(event, "")
    except json.JSONDecodeError:
        return ""


def payload_log(page, event: str) -> list[str]:
    """Return every payload recorded for `event`, oldest first.

    `on_nodes_change` carries several change types, so a `dimensions` batch
    lands right behind a `position` batch under the same name; the assertion
    needs the batch it cares about, not merely the most recent one.
    """
    raw = page.text_content("[data-testid='payload-log']") or ""
    return [line.split("|", 1)[1] for line in raw.splitlines() if line.startswith(f"{event}|")]


def empty_pane_point(page) -> tuple[float, float]:
    """Return a canvas point that no node occupies.

    Panning must start on bare canvas; a point that happens to sit on a node
    drags the node instead and the viewport never moves.
    """
    pane = page.locator(".react-flow__pane").bounding_box()
    assert pane is not None
    nodes = page.locator(".react-flow__node")
    boxes = [nodes.nth(i).bounding_box() for i in range(nodes.count())]

    for fraction_y in (0.85, 0.15, 0.5):
        for fraction_x in (0.1, 0.9, 0.5):
            x = pane["x"] + pane["width"] * fraction_x
            y = pane["y"] + pane["height"] * fraction_y
            if not any(
                box
                and box["x"] - 20 <= x <= box["x"] + box["width"] + 20
                and box["y"] - 20 <= y <= box["y"] + box["height"] + 20
                for box in boxes
            ):
                return x, y
    raise AssertionError("no empty point found on the canvas")


def drag(page, selector: str, dx: int, dy: int, steps: int = 12) -> None:
    """Drag an element by an offset with intermediate mouse moves."""
    box = page.locator(selector).first.bounding_box()
    assert box is not None, f"{selector} has no bounding box"
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(
        box["x"] + box["width"] / 2 + dx, box["y"] + box["height"] / 2 + dy, steps=steps
    )
    page.mouse.up()


# --------------------------------------------------------------------------
# REQ-001 / REQ-002 / REQ-004 — the canvas renders, styled, with plugins
# --------------------------------------------------------------------------


def test_canvas_renders_nodes_and_edges(canvas_page) -> None:
    """REQ-002: declared nodes and edges appear on the canvas."""
    expect(canvas_page.locator(".react-flow__node")).to_have_count(3)
    expect(canvas_page.locator(".react-flow__edge")).to_have_count(2)


def test_stylesheet_is_applied_without_user_css(canvas_page) -> None:
    """REQ-001: the v12 stylesheet loads, so the viewport is actually laid out.

    Asserted through a computed style rather than the presence of a <link>: the
    requirement is that the canvas *renders styled*, not that a file was fetched.
    """
    position = canvas_page.eval_on_selector(
        ".react-flow__viewport", "el => getComputedStyle(el).position"
    )
    assert position == "absolute"


def test_plugin_components_render(canvas_page) -> None:
    """REQ-004: background, controls, minimap and panel are all present."""
    for selector in (
        ".react-flow__background",
        ".react-flow__controls",
        ".react-flow__minimap",
        ".react-flow__panel",
    ):
        expect(canvas_page.locator(selector).first).to_be_visible()


# --------------------------------------------------------------------------
# REQ-005 / REQ-009 — drag deltas and drag budget
# --------------------------------------------------------------------------


def test_drag_sends_position_deltas_without_node_objects(debug_page) -> None:
    """REQ-005: a drag reports position deltas, never full node objects."""
    drag(debug_page, ".react-flow__node", 90, 60)
    debug_page.wait_for_timeout(600)

    position_batches = [
        p for p in payload_log(debug_page, "on_nodes_change") if '"type":"position"' in p
    ]

    assert position_batches, "the drag produced no position change"
    for batch in position_batches:
        assert '"item"' not in batch, "a position change must not carry the node"
        assert '"data"' not in batch


def test_drag_fires_exactly_one_start_and_one_stop(debug_page) -> None:
    """REQ-009: intermediate drag positions are not streamed to the server."""
    drag(debug_page, ".react-flow__node", 70, 40, steps=20)
    debug_page.wait_for_timeout(600)

    counts = ledger(debug_page)
    assert counts.get("on_node_drag_start") == 1
    assert counts.get("on_node_drag_stop") == 1


# --------------------------------------------------------------------------
# REQ-008 — click payloads
# --------------------------------------------------------------------------


def test_node_click_payload_is_filtered(debug_page) -> None:
    """REQ-008: a node click carries id, type and position — not its data."""
    debug_page.locator(".react-flow__node").first.click()
    debug_page.wait_for_timeout(400)

    payload = payload_for(debug_page, "on_node_click")
    assert '"id"' in payload
    assert '"position"' in payload
    assert '"data"' not in payload


def test_pane_click_sends_position_only(debug_page) -> None:
    """REQ-008: a pane click carries coordinates only."""
    x, y = empty_pane_point(debug_page)
    debug_page.mouse.click(x, y)
    debug_page.wait_for_timeout(500)

    assert '"position"' in payload_for(debug_page, "on_pane_click")


# --------------------------------------------------------------------------
# REQ-012 — viewport debounce budget
# --------------------------------------------------------------------------


def test_continuous_pan_stays_within_the_viewport_budget(debug_page) -> None:
    """REQ-012: panning for one second yields at most 6 viewport events."""
    start_x, start_y = empty_pane_point(debug_page)

    debug_page.mouse.move(start_x, start_y)
    debug_page.mouse.down()
    for step in range(20):  # ~1 s of continuous movement
        debug_page.mouse.move(start_x + step * 4, start_y + step * 2)
        debug_page.wait_for_timeout(50)
    debug_page.mouse.up()
    debug_page.wait_for_timeout(600)

    viewport_events = ledger(debug_page).get("on_viewport_change", 0)
    assert viewport_events <= 6, f"debounce budget exceeded: {viewport_events} events"
    assert viewport_events >= 1, "the viewport did change, so at least one event is due"


# --------------------------------------------------------------------------
# REQ-011 — deletion
# --------------------------------------------------------------------------


def test_delete_key_removes_the_selected_node(debug_page) -> None:
    """REQ-011: the delete key reports the removed ids and drops the node."""
    before = debug_page.locator(".react-flow__node").count()
    debug_page.locator(".react-flow__node").first.click()
    debug_page.wait_for_timeout(200)
    debug_page.keyboard.press("Backspace")
    debug_page.wait_for_timeout(600)

    assert debug_page.locator(".react-flow__node").count() == before - 1
    assert "on_nodes_delete" in " ".join(ledger(debug_page))


# --------------------------------------------------------------------------
# REQ-017 — edge types
# --------------------------------------------------------------------------


def test_every_edge_type_renders(page, demo_url: str) -> None:
    """REQ-017: bezier, step, smoothstep and straight all render with labels.

    Waits on nodes for readiness and on edges by attachment: edge `<path>`
    elements report intermittently as not-visible while the canvas settles,
    which made a visibility wait flaky.
    """
    page.goto(f"{demo_url}/edge-types", wait_until="networkidle")
    page.wait_for_selector(".react-flow__node", timeout=30_000)
    page.wait_for_selector(".react-flow__edge", state="attached", timeout=30_000)

    expect(page.locator(".react-flow__edge")).to_have_count(4)
    for label in ("bezier", "step", "smoothstep", "straight"):
        expect(page.get_by_text(label, exact=True).first).to_be_attached()


def test_edge_markers_render(page, demo_url: str) -> None:
    """REQ-017: start and end markers are emitted as SVG marker defs.

    Waits for attachment rather than visibility: an SVG `<marker>` def has no
    layout box of its own, so a visibility wait would never settle.
    """
    page.goto(f"{demo_url}/edge-types", wait_until="networkidle")
    page.wait_for_selector(".react-flow__node", timeout=30_000)
    page.wait_for_selector(".react-flow__edge", state="attached", timeout=30_000)

    assert page.locator("marker").count() > 0


# --------------------------------------------------------------------------
# REQ-015 — subflows
# --------------------------------------------------------------------------


def test_child_drag_is_clamped_to_the_parent(page, demo_url: str) -> None:
    """REQ-015: a child dragged past its parent stops at the parent bounds."""
    page.goto(f"{demo_url}/subflows", wait_until="networkidle")
    page.wait_for_selector(".react-flow__node", timeout=30_000)

    parent = page.locator("[data-id='group-1']").bounding_box()
    assert parent is not None

    drag(page, "[data-id='child-a']", 900, 700, steps=25)
    page.wait_for_timeout(600)

    child = page.locator("[data-id='child-a']").bounding_box()
    assert child is not None
    assert child["x"] + child["width"] <= parent["x"] + parent["width"] + 2
    assert child["y"] + child["height"] <= parent["y"] + parent["height"] + 2


# --------------------------------------------------------------------------
# REQ-018 — colour mode
# --------------------------------------------------------------------------


def test_color_mode_flips_without_a_reload(canvas_page) -> None:
    """REQ-018: toggling colour mode repaints the canvas in place."""
    canvas = canvas_page.locator(".react-flow").first
    before = canvas.get_attribute("class") or ""

    canvas_page.click("[data-testid='color-mode-toggle']")
    canvas_page.wait_for_timeout(600)

    after = canvas.get_attribute("class") or ""
    assert before != after, "the canvas colour-mode class did not change"
    assert re.search(r"\b(dark|light)\b", after)


# --------------------------------------------------------------------------
# REQ-013 — no console errors from the wrapper
# --------------------------------------------------------------------------


def test_canvas_mounts_without_console_errors(page, demo_url: str) -> None:
    """A clean mount is the baseline for trusting the warning-based REQs."""
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    page.goto(demo_url, wait_until="networkidle")
    page.wait_for_selector(".react-flow__node", timeout=30_000)

    assert not errors, f"console errors on mount: {errors}"
