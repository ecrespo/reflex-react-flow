"""T-008 — event_utils.js tests (Tech Design DD-002/DD-003).

Covers REQ-005/006 (delta-only payloads), REQ-012 (debounce mechanism) and
REQ-013 (32 KB cap with truncation + console warning).

The helpers are plain JavaScript with no DOM or React dependency, so they are
driven directly through Node in a one-shot harness. This gives T-008 a local,
self-verifiable Done criterion (analyze finding A-06) instead of deferring all
evidence to the Playwright suite in T-012.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


def serialized_size(payload: object) -> int:
    """Byte length of `payload` as it actually travels over the socket.

    `JSON.stringify` emits compact JSON; Python's `json.dumps` defaults to spaces
    after ":" and ",". Measuring with the default separators would overstate the
    payload by ~7% and make this assertion disagree with the cap the JS enforces.
    """
    return len(json.dumps(payload, separators=(",", ":")).encode())


ASSET = (
    Path(__file__).resolve().parents[2]
    / "custom_components"
    / "reflex_react_flow"
    / "assets"
    / "event_utils.js"
)

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js is required to drive the JS helpers"
)


def run_js(script: str) -> dict:
    """Execute `script` with the asset imported, returning its JSON result.

    The harness captures console warnings so tests can assert on them the same
    way a browser user would observe them.
    """
    harness = f"""
const warnings = [];
const originalWarn = console.warn;
console.warn = (...args) => {{ warnings.push(args.join(" ")); }};

{ASSET.read_text()}

// `await` so helpers under test may return a promise (the debounce cases do);
// without it JSON.stringify would serialize the pending promise as `{{}}`.
let result;
try {{
  result = await (async function () {{ {script} }})();
}} finally {{
  console.warn = originalWarn;
}}
originalWarn(JSON.stringify({{ result, warnings }}));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", harness],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"node failed:\n{completed.stderr}")
    return json.loads(completed.stderr.strip().splitlines()[-1])


# --------------------------------------------------------------------------
# REQ-005 / REQ-006 — delta-only payloads
# --------------------------------------------------------------------------


def test_position_change_keeps_only_delta_fields() -> None:
    """REQ-005: a position change carries id/type/position/dragging, never the node."""
    payload = run_js("""
      return rrfFilterNodeChanges([{
        id: "n1", type: "position",
        position: {x: 10, y: 20}, dragging: true,
        item: {id: "n1", data: {huge: "x".repeat(1000)}},
        extraneous: "should be dropped"
      }], 32);
    """)["result"]

    assert payload == [
        {"id": "n1", "type": "position", "position": {"x": 10, "y": 20}, "dragging": True}
    ]


def test_select_and_remove_changes_carry_no_item() -> None:
    """REQ-005: select/remove changes must not smuggle full node objects."""
    payload = run_js("""
      return rrfFilterNodeChanges([
        {id: "a", type: "select", selected: true, item: {data: {}}},
        {id: "b", type: "remove", item: {data: {}}}
      ], 32);
    """)["result"]

    assert payload == [
        {"id": "a", "type": "select", "selected": True},
        {"id": "b", "type": "remove"},
    ]


def test_add_and_replace_changes_keep_item() -> None:
    """Data Model §3.1: `item` is legitimate for add/replace only."""
    payload = run_js("""
      return rrfFilterNodeChanges([
        {type: "add", item: {id: "n2", position: {x: 0, y: 0}}}
      ], 32);
    """)["result"]

    assert payload[0]["type"] == "add"
    assert payload[0]["item"]["id"] == "n2"


def test_edge_changes_are_filtered() -> None:
    """REQ-006: edge changes carry id/type and per-type fields only."""
    payload = run_js("""
      return rrfFilterEdgeChanges([
        {id: "e1", type: "select", selected: false, item: {data: {}}},
        {id: "e2", type: "remove"}
      ], 32);
    """)["result"]

    assert payload == [
        {"id": "e1", "type": "select", "selected": False},
        {"id": "e2", "type": "remove"},
    ]


def test_connection_payload_is_exactly_four_fields() -> None:
    """REQ-007: on_connect delivers exactly source/target/sourceHandle/targetHandle."""
    payload = run_js("""
      return rrfFilterConnection({
        source: "a", target: "b", sourceHandle: "out", targetHandle: "in",
        extra: "dropped"
      });
    """)["result"]

    assert payload == {
        "source": "a",
        "target": "b",
        "source_handle": "out",
        "target_handle": "in",
    }


# --------------------------------------------------------------------------
# REQ-013 — payload cap
# --------------------------------------------------------------------------


def test_oversized_batch_is_truncated_and_warns() -> None:
    """REQ-013: a 500-change batch is truncated to fit and warns, never blocks."""
    outcome = run_js("""
      const changes = [];
      for (let i = 0; i < 500; i++) {
        changes.push({id: "node-" + i, type: "position",
                      position: {x: i * 1.123456789, y: i * 9.87654321}, dragging: true});
      }
      return rrfFilterNodeChanges(changes, 2);
    """)

    payload, warnings = outcome["result"], outcome["warnings"]

    assert len(payload) < 500, "oversized batch must be truncated"
    assert payload, "truncation must still deliver a payload, not drop everything"
    assert serialized_size(payload) <= 2 * 1024
    assert any("reflex-react-flow" in w for w in warnings)
    assert any("on_nodes_change" in w for w in warnings)


def test_batch_within_cap_is_untouched_and_silent() -> None:
    """REQ-013: payloads under the cap pass through with no warning."""
    outcome = run_js("""
      return rrfFilterNodeChanges(
        [{id: "n1", type: "select", selected: true}], 32);
    """)

    assert len(outcome["result"]) == 1
    assert outcome["warnings"] == []


def test_truncation_keeps_the_earliest_changes() -> None:
    """REQ-013: the tail is dropped, so the surviving prefix stays contiguous."""
    payload = run_js("""
      const changes = [];
      for (let i = 0; i < 200; i++) {
        changes.push({id: "n" + i, type: "select", selected: true});
      }
      return rrfFilterNodeChanges(changes, 1);
    """)["result"]

    assert payload[0]["id"] == "n0"
    ids = [entry["id"] for entry in payload]
    assert ids == [f"n{i}" for i in range(len(ids))]


# --------------------------------------------------------------------------
# REQ-012 — debounce
# --------------------------------------------------------------------------


def test_debounce_collapses_rapid_calls_to_one_trailing_call() -> None:
    """REQ-012: N rapid viewport updates collapse into a single trailing call."""
    outcome = run_js("""
      return new Promise((resolve) => {
        const seen = [];
        const debounced = rrfDebounce((v) => seen.push(v), 20);
        for (let i = 0; i < 10; i++) debounced(i);
        setTimeout(() => resolve({calls: seen.length, last: seen[seen.length - 1]}), 80);
      });
    """)

    # The harness returns the resolved promise value.
    assert outcome["result"]["calls"] == 1
    assert outcome["result"]["last"] == 9, "trailing edge delivers the newest value"


def test_debounce_allows_separated_calls_through() -> None:
    """REQ-012: calls spaced beyond the interval are not swallowed."""
    outcome = run_js("""
      return new Promise((resolve) => {
        const seen = [];
        const debounced = rrfDebounce((v) => seen.push(v), 10);
        debounced("first");
        setTimeout(() => debounced("second"), 60);
        setTimeout(() => resolve({calls: seen.length}), 140);
      });
    """)

    assert outcome["result"]["calls"] == 2


def test_keyed_debounce_survives_wrapper_recreation() -> None:
    """REQ-012: the timer must not live in a closure React can throw away.

    Reflex re-renders the canvas on every state update, which re-creates the
    event handler. A closure-held timer would restart each time and never
    coalesce, so the timer is keyed on the canvas instead.
    """
    outcome = run_js("""
      return new Promise((resolve) => {
        const seen = [];
        // Simulate 10 rapid viewport updates across 10 separate re-renders:
        // each iteration builds a brand-new wrapper, as React would.
        for (let i = 0; i < 10; i++) {
          rrfDebounceKeyed("canvas-1", () => seen.push(i), 20);
        }
        setTimeout(() => resolve({calls: seen.length, last: seen[seen.length - 1]}), 90);
      });
    """)

    assert outcome["result"]["calls"] == 1, "re-created wrappers must still coalesce"
    assert outcome["result"]["last"] == 9


def test_keyed_debounce_isolates_separate_canvases() -> None:
    """REQ-012: two canvases on one page must not share a debounce timer."""
    outcome = run_js("""
      return new Promise((resolve) => {
        const seen = [];
        rrfDebounceKeyed("canvas-a", () => seen.push("a"), 20);
        rrfDebounceKeyed("canvas-b", () => seen.push("b"), 20);
        setTimeout(() => resolve({seen}), 90);
      });
    """)

    assert sorted(outcome["result"]["seen"]) == ["a", "b"]


def test_unchanged_selection_is_not_resent() -> None:
    """REQ-010: a repeat of the same selection must not reach the socket.

    React Flow re-fires onSelectionChange whenever the `nodes` prop changes
    identity; with a literal node list each state update re-renders it, so an
    undeduplicated selection event feeds itself forever.
    """
    outcome = run_js("""
      const seen = [];
      const send = (p) => rrfDedupeKeyed("canvas-1:selection", p, () => seen.push(p));
      for (let i = 0; i < 5; i++) send({node_ids: [], edge_ids: []});
      send({node_ids: ["n1"], edge_ids: []});
      send({node_ids: ["n1"], edge_ids: []});
      send({node_ids: [], edge_ids: []});
      return {seen};
    """)

    assert outcome["result"]["seen"] == [
        {"node_ids": [], "edge_ids": []},
        {"node_ids": ["n1"], "edge_ids": []},
        {"node_ids": [], "edge_ids": []},
    ]


def test_selection_dedupe_isolates_separate_canvases() -> None:
    """REQ-010: one canvas's selection must not suppress another's."""
    outcome = run_js("""
      const seen = [];
      rrfDedupeKeyed("canvas-a:selection", {node_ids: []}, () => seen.push("a"));
      rrfDedupeKeyed("canvas-b:selection", {node_ids: []}, () => seen.push("b"));
      return {seen};
    """)

    assert outcome["result"]["seen"] == ["a", "b"]


def test_viewport_payload_is_rounded_and_minimal() -> None:
    """REQ-012 / Data Model §3.4: viewport carries x, y, zoom only."""
    payload = run_js("""
      return rrfFilterViewport({x: 1.23456789, y: -4.5, zoom: 1.5, extra: "dropped"});
    """)["result"]

    assert set(payload) == {"x", "y", "zoom"}
    assert payload["zoom"] == 1.5
