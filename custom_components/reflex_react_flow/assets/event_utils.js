/**
 * reflex-react-flow — event payload helpers.
 *
 * The WebSocket is the scarce resource (Constitution Art. 6): React Flow's raw
 * callbacks carry whole node objects and React synthetic events, which would
 * saturate the channel well before a graph gets interesting. Every helper here
 * runs in the browser *before* a payload is serialized into a Reflex event, so
 * only whitelisted delta fields ever travel.
 *
 * Kept dependency-free and DOM-free on purpose: these are pure functions, driven
 * directly by the Python test suite through Node (tests/unit/test_event_utils.py).
 *
 * Normative payload schemas: specs/data-model/reflex-react-flow-schema.md §3.
 */

const RRF_LOG_PREFIX = "[reflex-react-flow]";

/**
 * Fields carried by each node-change type (Data Model §3.1).
 *
 * A dispatch table rather than a switch: adding a change type is a new entry,
 * not an edit to control flow (Tech Design §5.2.1, OCP).
 */
const RRF_NODE_CHANGE_FIELDS = {
  position: ["position", "dragging"],
  dimensions: ["dimensions"],
  select: ["selected"],
  remove: [],
  add: ["item"],
  replace: ["item"],
};

/** Fields carried by each edge-change type (Data Model §3.2). */
const RRF_EDGE_CHANGE_FIELDS = {
  select: ["selected"],
  remove: [],
  add: ["item"],
  replace: ["item"],
};

/**
 * Project one change onto the fields its type is allowed to carry.
 *
 * Unknown change types degrade to `{id, type}` rather than passing the raw
 * object through: an unrecognised type must never become a hole in the filter.
 */
function rrfProjectChange(change, fieldsByType) {
  const projected = {};
  if (change.id !== undefined) projected.id = change.id;
  projected.type = change.type;

  const allowed = fieldsByType[change.type];
  if (allowed === undefined) {
    console.warn(
      `${RRF_LOG_PREFIX} unknown change type "${change.type}"; sending id and type only`,
    );
    return projected;
  }

  for (const field of allowed) {
    if (change[field] !== undefined) projected[field] = change[field];
  }
  return projected;
}

/** Serialized byte length of a payload, as it will travel over the socket. */
function rrfByteLength(payload) {
  return new TextEncoder().encode(JSON.stringify(payload)).length;
}

/**
 * Drop changes from the tail until the payload fits under `capKb` (REQ-013).
 *
 * Truncating beats blocking: an oversized batch still delivers its earliest
 * changes and warns, so the canvas stays responsive instead of stalling the
 * socket. At least one change is always kept — delivering nothing would look
 * like a silent failure.
 */
function rrfEnforceCap(changes, capKb, eventName) {
  const capBytes = capKb * 1024;
  if (rrfByteLength(changes) <= capBytes) return changes;

  let kept = changes;
  while (kept.length > 1 && rrfByteLength(kept) > capBytes) {
    // Halve first for large overshoots, then step down to land just under.
    const step = rrfByteLength(kept) > capBytes * 2 ? Math.ceil(kept.length / 2) : 1;
    kept = kept.slice(0, Math.max(1, kept.length - step));
  }

  console.warn(
    `${RRF_LOG_PREFIX} ${eventName} payload exceeded ${capKb} KB; ` +
      `truncated ${changes.length} changes to ${kept.length}`,
  );
  return kept;
}

/** Filter an onNodesChange payload to delta fields only (REQ-005, REQ-013). */
function rrfFilterNodeChanges(changes, capKb) {
  const projected = (changes || []).map((change) =>
    rrfProjectChange(change, RRF_NODE_CHANGE_FIELDS),
  );
  return rrfEnforceCap(projected, capKb, "on_nodes_change");
}

/** Filter an onEdgesChange payload to delta fields only (REQ-006, REQ-013). */
function rrfFilterEdgeChanges(changes, capKb) {
  const projected = (changes || []).map((change) =>
    rrfProjectChange(change, RRF_EDGE_CHANGE_FIELDS),
  );
  return rrfEnforceCap(projected, capKb, "on_edges_change");
}

/**
 * Filter a completed connection (REQ-007).
 *
 * Handle keys are snake_cased here because this payload is consumed as Python
 * keyword arguments, unlike the change deltas which stay in React's vocabulary.
 */
function rrfFilterConnection(connection) {
  return {
    source: connection.source ?? null,
    target: connection.target ?? null,
    source_handle: connection.sourceHandle ?? null,
    target_handle: connection.targetHandle ?? null,
  };
}

/** Filter onConnectStart (REQ-014). */
function rrfFilterConnectStart(event, params) {
  const details = params || {};
  return {
    node_id: details.nodeId ?? null,
    handle_id: details.handleId ?? null,
    handle_type: details.handleType ?? null,
  };
}

/** Filter onConnectEnd (REQ-014): success is all the server needs. */
function rrfFilterConnectEnd(event, connectionState) {
  return { connected: Boolean(connectionState && connectionState.isValid) };
}

/** Filter a node click/drag payload to `{id, type, position}` (REQ-008, REQ-009). */
function rrfFilterNode(event, node) {
  return {
    id: node.id,
    type: node.type ?? "default",
    position: { x: node.position.x, y: node.position.y },
  };
}

/** Filter a node drag payload to `{id, position}` (REQ-009). */
function rrfFilterNodeDrag(event, node) {
  return { id: node.id, position: { x: node.position.x, y: node.position.y } };
}

/** Filter an edge click payload to `{id, type}` (REQ-008). */
function rrfFilterEdge(event, edge) {
  return { id: edge.id, type: edge.type ?? "bezier" };
}

/**
 * Filter a pane click to flow coordinates (REQ-008).
 *
 * Only the position travels — a React synthetic event is not serializable and
 * would be worthless on the server anyway.
 */
function rrfFilterPaneClick(event) {
  return { position: { x: event.clientX ?? 0, y: event.clientY ?? 0 } };
}

/** Filter a selection change to id lists (REQ-010). */
function rrfFilterSelection(params) {
  const selection = params || {};
  return {
    node_ids: (selection.nodes || []).map((node) => node.id),
    edge_ids: (selection.edges || []).map((edge) => edge.id),
  };
}

/** Reduce a deleted-elements payload to ids (REQ-011). */
function rrfFilterDeleted(elements) {
  return (elements || []).map((element) => element.id);
}

/** Filter a viewport to `{x, y, zoom}` (REQ-012). */
function rrfFilterViewport(viewport) {
  return { x: viewport.x, y: viewport.y, zoom: viewport.zoom };
}

/**
 * Trailing-edge debounce (REQ-012, DD-003).
 *
 * Trailing rather than leading: the server wants where the viewport *ended up*,
 * not where a pan gesture started. Streaming intermediate frames at 60 Hz is
 * exactly what Art. 6 forbids.
 */
function rrfDebounce(fn, waitMs) {
  let timer = null;
  return function debounced(...args) {
    if (timer !== null) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      fn(...args);
    }, waitMs);
  };
}

/**
 * Timers for {@link rrfDebounceKeyed}, keyed by canvas instance.
 *
 * A plain closure debounce loses its timer whenever React re-creates the
 * wrapper, which happens on every Reflex state update — the gesture would then
 * never coalesce. Holding the timer in a module-level map keyed by a token the
 * Python side mints per canvas makes the debounce survive re-renders.
 */
const RRF_TIMERS = new Map();

/** Trailing-edge debounce whose timer is keyed, not closed over (REQ-012). */
function rrfDebounceKeyed(key, fn, waitMs) {
  const existing = RRF_TIMERS.get(key);
  if (existing !== undefined) clearTimeout(existing);
  RRF_TIMERS.set(
    key,
    setTimeout(() => {
      RRF_TIMERS.delete(key);
      fn();
    }, waitMs),
  );
}

/**
 * Last payload signature sent per canvas, for {@link rrfDedupeKeyed}.
 *
 * Keyed for the same reason as {@link RRF_TIMERS}: the wrapper closure is
 * re-created on every Reflex state update, so it cannot hold the memory itself.
 */
const RRF_LAST_SENT = new Map();

/**
 * Call `fn` only when `payload` differs from the last one sent under `key` (REQ-010).
 *
 * React Flow fires onSelectionChange whenever the `nodes` prop changes identity,
 * not only when the selection does. A canvas fed a literal list gets a fresh
 * array on every re-render, and the state update triggered by the event causes
 * that re-render — an unbounded feedback loop over the socket (Art. 6). Dropping
 * repeats of an unchanged selection breaks the loop.
 */
function rrfDedupeKeyed(key, payload, fn) {
  const signature = JSON.stringify(payload);
  if (RRF_LAST_SENT.get(key) === signature) return;
  RRF_LAST_SENT.set(key, signature);
  fn();
}

export {
  RRF_LAST_SENT,
  RRF_TIMERS,
  rrfDebounce,
  rrfDebounceKeyed,
  rrfDedupeKeyed,
  rrfFilterConnectEnd,
  rrfFilterConnectStart,
  rrfFilterConnection,
  rrfFilterDeleted,
  rrfFilterEdge,
  rrfFilterEdgeChanges,
  rrfFilterNode,
  rrfFilterNodeChanges,
  rrfFilterNodeDrag,
  rrfFilterPaneClick,
  rrfFilterSelection,
  rrfFilterViewport,
};
