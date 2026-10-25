# reflex-react-flow

## Product Requirements Document (PRD)

| Field | Value |
|---|---|
| **Author** | Ernesto Crespo |
| **Status** | `DRAFT` |
| **Version** | 1.0 |
| **Date** | 2026-08-08 |
| **Reviewers** | — |
| **Last updated** | 2026-08-08 |
| **Constitution** | [specs/constitution.md](../constitution.md) |

---

## 1. Executive Summary

`reflex-react-flow` is an open source (MIT) custom component for the Reflex framework
that wraps `@xyflow/react` v12 (React Flow), letting Python developers build node
editors, flow charts, and agent-graph visualizations from pure Python — zero
JavaScript required for ~90% of use cases.

The package ships in three layers: (1) a declarative 1:1 wrapper of the prop-driven
React Flow API with WebSocket-safe filtered events, (2) a registry of parameterizable
generic nodes (card, agent, group, annotation, io) fully driven from `node.data`, and
(3) a high-level Python API (`FlowState`, server-side layouts with `networkx`, and an
optional LangGraph adapter). It is distributed on PyPI as `reflex-react-flow`, import
namespace `reflex_react_flow` (documented alias `rxf`).

## 2. Context and Problem

### 2.1 Current situation
No community React Flow wrapper for Reflex exists on PyPI. The only complete wrapper
("Reflex Flow") lives inside `reflex-enterprise` under commercial terms. The official
Reflex wrapping tutorial uses the legacy `reactflow` v11 package and covers roughly
10% of the API.

### 2.2 Problem
Python developers building agentic tooling (LangGraph, LightAgent) and data pipelines
have no open source way to render interactive graphs in Reflex without writing
JavaScript, maintaining their own fragile wrapper, or paying for enterprise licensing.

### 2.3 Opportunity
A clean-room, MIT-licensed, v12-based wrapper with a Python-first API fills a real
gap with a clear audience, and can become the reference graph component in the Reflex
custom-component gallery.

## 3. Target Users

### Persona 1: Python app developer
- **Description:** Builds internal tools/dashboards in Reflex; visualizes pipelines, ETL flows, org charts.
- **Primary need:** Render and edit graphs declaratively from Python; never touch JS.
- **Usage frequency:** Weekly
- **Technical level:** Medium (Python high, JS low/none)

### Persona 2: Agentic-tooling developer
- **Description:** Builds LangGraph/LightAgent-based agents; needs to show agent graphs and live execution state.
- **Primary need:** Turn a compiled `StateGraph` into a rendered, live-updating graph with agent status.
- **Usage frequency:** Daily during development
- **Technical level:** High (Python), low (JS)

### Persona 3: Advanced component developer
- **Description:** Comfortable with React; needs custom node visuals beyond the registry.
- **Primary need:** A documented escape hatch to register their own `.jsx` node types.
- **Usage frequency:** Occasional
- **Technical level:** High (Python + JS)

## 4. Goals and Success Metrics

### 4.1 Project goals

| Goal | Metric | Target | Horizon |
|---|---|---|---|
| Fill the wrapper gap | Published on PyPI, listed in Reflex component gallery | v0.1.0 live | Phase 4 |
| Adoption | GitHub stars / PyPI downloads month 3 | 100 stars / 500 dl-mo | +3 months post-launch |
| Zero-JS promise | Documented use cases needing user JSX | ≤ 10% | Continuous |
| Trust | Test coverage of MUST requirements | 100% (each REQ cited by ≥1 test) | Every release |

### 4.2 User goals

| User goal | Indicator |
|---|---|
| Render a graph in < 15 lines of Python | Quickstart example line count |
| Visualize a LangGraph agent in 1 call | `from_langgraph()` works on the demo graph |
| No WebSocket saturation on drag | Filtered payloads; drag a 200-node graph without disconnects |

## 5. Scope

### 5.1 In scope
- [ ] Layer 1: `ReactFlow` wrapper (v12, named imports, CSS injection), plugin components (`Background`, `Controls`, `MiniMap`, `Panel`, `NodeToolbar`, `NodeResizer`), filtered event specs, `Node`/`Edge`/`Viewport` Python models, subflows, multiple handles, edge markers/labels/types.
- [ ] Layer 2: generic-node registry (`card_node`, `agent_node`, `group_node`, `annotation_node`, `io_node`) driven by `node.data`; declarative handle config; JSX escape hatch.
- [ ] Layer 3: `FlowState` (ComponentState) with graph operations and `apply_changes`; server-side layouts (hierarchical, force, circular, layered) via `networkx`; optional `[langgraph]` extra with `from_langgraph()`.
- [ ] Demo Reflex app used for integration tests and documentation.
- [ ] PyPI packaging, CI, docs with v12 parity table.

### 5.2 Out of scope
- Pro-tier xyflow features (advanced undo/redo, copy/paste, helper lines) — prohibited sources per Constitution Art. 1; may be designed from scratch later as separate features.
- Client-side JS layout engines (dagre/elk in browser) — layouts are server-side Python by design.
- Realtime multi-user collaboration — out of scope for v1.
- Graph persistence/storage — the host app owns persistence.
- React Flow Components/UI kits beyond the plugin components listed above.

### 5.3 Future considerations
- Sibling package `reflex-langgraph-flow` if the adapter grows (decided in Implementation Plan).
- Minimap/thumbnail export (PNG).
- Undo/redo designed clean-room from scratch.

## 6. Functional Requirements (EARS)

Priority: every REQ below is `MUST` unless the **priority** column of its heading says
otherwise (`SHOULD`). Parenthesised names in headings are **EARS pattern** names
(ubiquitous / event / undesired / optional-feature), not priorities — the `WHERE`
("optional-feature") pattern does not lower a requirement's priority (A-05).

IDs are stable and allocated in blocks per layer (001–018 Layer 1, 020–025 Layer 2,
030–037 Layer 3); gaps between blocks (e.g. 019, 026–029) are intentional and are not
ghost requirements (A-07). A removed REQ retires its ID.

### 6.1 Layer 1 — Declarative wrapper

**REQ-001 (ubiquitous):** THE SYSTEM SHALL wrap `@xyflow/react` v12.x using named
imports and SHALL inject `@xyflow/react/dist/style.css` via the component's custom
code so the canvas renders styled without user action.
*Observable: demo app renders a styled canvas with no user-added CSS.*

**REQ-002 (event):** WHEN a Reflex app declares `react_flow(nodes=[...], edges=[...])`
with valid `Node`/`Edge` data, THE SYSTEM SHALL render those nodes and edges on the
canvas.
*Observable: Playwright test finds the node/edge DOM elements by id.*

**REQ-003 (ubiquitous):** THE SYSTEM SHALL expose as snake_case Python props:
`node_types`, `edge_types`, `color_mode` ("light"|"dark"|"system"), `fit_view`,
`default_edge_options`, `connection_mode`, `snap_to_grid`, `snap_grid`, `min_zoom`,
`max_zoom`, `translate_extent`, `node_extent`, `nodes_draggable`,
`nodes_connectable`, `nodes_focusable`, `edges_focusable`, `elements_selectable`,
`pan_on_drag`, `zoom_on_scroll`, `delete_key_code`, `viewport`, `default_viewport`.
*Observable: each prop reaches the rendered React component with the camelCase name (unit test on rendered component dict).*

**REQ-004 (ubiquitous):** THE SYSTEM SHALL provide wrapped plugin components
`background` (variants dots/lines/cross), `controls`, `mini_map`, `panel`,
`node_toolbar`, `node_resizer`, composable as children of `react_flow`.
*Observable: demo page renders each plugin component; DOM assertions per component.*

**REQ-005 (event):** WHEN nodes change in the browser (drag, select, dimension,
remove), THE SYSTEM SHALL fire `on_nodes_change` whose payload contains only the
change deltas (`id`, `type`, and the fields of that change type), never full node
objects.
*Observable: event-spec unit test asserts payload shape; integration test asserts a drag produces `position` changes only.*

**REQ-006 (event):** WHEN edges change in the browser (select, remove), THE SYSTEM
SHALL fire `on_edges_change` with change deltas only (`id`, `type`, per-type fields).
*Observable: event-spec unit test.*

**REQ-007 (event):** WHEN the user completes a connection gesture, THE SYSTEM SHALL
fire `on_connect` with exactly `{source, target, source_handle, target_handle}`.
*Observable: integration test connects two nodes and asserts the received payload.*

**REQ-008 (event):** WHEN the user clicks or double-clicks a node, clicks an edge, or
clicks the pane, THE SYSTEM SHALL fire the corresponding event
(`on_node_click`, `on_node_double_click`, `on_edge_click`, `on_pane_click`) with a
filtered payload: element `id`, `type`, and `position` (pane click: canvas
coordinates only).
*Observable: integration tests per event assert payload fields and absence of `data`.*

**REQ-009 (event):** WHEN a node drag starts or stops, THE SYSTEM SHALL fire
`on_node_drag_start` / `on_node_drag_stop` with `{id, position}` only; THE SYSTEM
SHALL NOT stream intermediate drag-move positions to the server.
*Observable: integration test counts server events during a drag: exactly 1 start + 1 stop (plus batched `on_nodes_change`).*

**REQ-010 (event):** WHEN the selection changes, THE SYSTEM SHALL fire
`on_selection_change` with `{node_ids: [...], edge_ids: [...]}` only.
*Observable: event-spec unit test.*

**REQ-011 (event):** WHEN nodes or edges are deleted, THE SYSTEM SHALL fire
`on_nodes_delete` / `on_edges_delete` with the list of deleted ids only.
*Observable: integration test deletes a node with `delete_key_code` and asserts payload.*

**REQ-012 (event):** WHEN the viewport changes, THE SYSTEM SHALL fire
`on_viewport_change` with `{x, y, zoom}` debounced by a configurable interval
(default 200 ms).
*Observable: integration test pans continuously for 1 s and asserts ≤ 6 server events.*

**REQ-013 (undesired):** IF a single serialized event payload exceeds 32 KB, THEN THE
SYSTEM SHALL truncate the change list to fit, emit a browser console warning naming
the event, and deliver the truncated payload rather than block the WebSocket.
*Observable: unit test with a synthetic 500-change batch asserts truncation + warning hook.*

**REQ-014 (event):** WHEN `on_connect_start` / `on_connect_end` fire, THE SYSTEM
SHALL deliver `{node_id, handle_id, handle_type}` (start) and connection success
boolean (end) only.
*Observable: event-spec unit test.*

**REQ-015 (ubiquitous):** THE SYSTEM SHALL support subflows: a child `Node` with
`parent_id` and `extent="parent"` whose parent is of type `group_node` (or the
compatible built-in alias `"group"`, Data Model §2.1) SHALL render nested inside its
parent and clamp dragging to the parent bounds.
*Observable: integration test drags a child beyond parent bounds and asserts clamped position.*

**REQ-016 (undesired):** IF a `Node` or `Edge` is constructed in Python without a
required field (`id`, `position` for nodes; `id`, `source`, `target` for edges), THEN
THE SYSTEM SHALL raise `ValueError` at construction time with the field name in the
message.
*Observable: pytest asserts the exception and message.*

**REQ-017 (ubiquitous):** THE SYSTEM SHALL support edge types `bezier` (default),
`step`, `smoothstep`, `straight`, edge `label`, and start/end markers
(arrow/arrowclosed) declared from Python.
*Observable: demo page renders one edge of each type; DOM assertions.*

**REQ-018 (optional-feature pattern, priority MUST):** WHERE `color_mode="system"` is set, THE SYSTEM SHALL follow
the OS/browser color scheme without a page reload.
*Observable: Playwright emulates `prefers-color-scheme` change and asserts the canvas class flips.*

### 6.2 Layer 2 — Generic node registry

**REQ-020 (ubiquitous):** THE SYSTEM SHALL register by default the node types
`card_node`, `agent_node`, `group_node`, `annotation_node`, `io_node`, implemented in
a local `.jsx` asset, whose entire rendered content is controlled by `node.data`
(schemas in the Data Model spec) with no user-written JSX.
*Observable: demo page renders all 5 types from Python dicts only.*

**REQ-021 (ubiquitous):** THE SYSTEM SHALL render node handles declaratively from
`node.data.handles` (list of `{id, type, position}`), supporting multiple handles per
node.
*Observable: integration test renders a node with 3 handles and connects to a specific `handle_id`.*

**REQ-022 (event):** WHEN `node.data.status` of an `agent_node` changes
(idle/running/done/error) via state update, THE SYSTEM SHALL update the node's visual
status indicator without re-mounting the node.
*Observable: integration test flips status and asserts indicator class change while DOM node identity persists.*

**REQ-023 (undesired):** IF a `Node.type` references a type absent from both the
registry and user `node_types`, THEN THE SYSTEM SHALL render the React Flow default
node and emit a browser console warning naming the missing type.
*Observable: integration test with a bogus type asserts default-node render + console warning.*

**REQ-024 (undesired):** IF `node.data` lacks optional keys for its registry type,
THEN THE SYSTEM SHALL render the node with documented defaults (empty strings, no
badge, single default handle) and SHALL NOT crash.
*Observable: demo renders each registry type with `data={}`; no console error.*

**REQ-025 (ubiquitous):** THE SYSTEM SHALL document and support an escape hatch: a
user-supplied `.jsx` asset registered via `node_types` renders like a built-in type.
*Observable: demo app includes one custom user node; integration test asserts render.*

### 6.3 Layer 3 — High-level Python API

**REQ-030 (ubiquitous):** THE SYSTEM SHALL provide `FlowState`
(`rx.ComponentState`-based) encapsulating `nodes`, `edges`, and current selection,
with operations `add_node`, `remove_node`, `add_edge`, `remove_edge`,
`update_node_data`, `clear`.
*Observable: pytest unit tests per operation on state contents.*

**REQ-031 (event):** WHEN `on_nodes_change` / `on_edges_change` payloads arrive, THE
SYSTEM SHALL apply them to state via `apply_node_changes` / `apply_edge_changes`
(Python reimplementation of the xyflow helpers, clean-room from public docs),
supporting change types add/remove/position/dimensions/select/replace.
*Observable: pytest table-driven test: each change type mutates state as specified.*

**REQ-032 (undesired):** IF a change references an `id` not present in state, THEN
THE SYSTEM SHALL skip that change and log a Python warning, without raising.
*Observable: pytest asserts state unchanged + warning captured.*

**REQ-033 (ubiquitous):** THE SYSTEM SHALL provide server-side layout functions
`layout_hierarchical` (dagre-like layered), `layout_force`, `layout_circular`,
`layout_layered`, computed in Python with `networkx` (and/or `grandalf`), returning
nodes with updated positions; zero JavaScript layout code.
*Observable: pytest asserts deterministic positions (seeded) and no overlapping nodes for a 20-node DAG.*

**REQ-034 (undesired):** IF `layout_hierarchical` receives a cyclic graph, THEN THE
SYSTEM SHALL break cycles (feedback arc heuristic), complete the layout, and log a
warning listing removed-for-layout edges; it SHALL NOT raise.
*Observable: pytest with a cyclic graph asserts positions assigned + warning.*

**REQ-035 (optional, SHOULD):** WHERE the `[langgraph]` extra is installed, THE
SYSTEM SHALL provide `from_langgraph(compiled_graph)` producing `agent_node` nodes
and edges from a compiled LangGraph `StateGraph`, ready to render.
*Observable: pytest with a 3-node demo StateGraph asserts produced nodes/edges/types.*

**REQ-036 (undesired, SHOULD):** IF `from_langgraph` is called without `langgraph`
installed, THEN THE SYSTEM SHALL raise `ImportError` with the install hint
`pip install reflex-react-flow[langgraph]`.
*Observable: pytest without the extra asserts the message.*

**REQ-037 (undesired):** IF `FlowState.add_edge` receives a connection whose
`(source, source_handle, target, target_handle)` tuple already exists in `edges`, THEN
THE SYSTEM SHALL skip the insertion and emit a Python warning naming the existing edge
id, without raising — UNLESS the state declares `allow_duplicate_edges = True`, in
which case the duplicate SHALL be added with a fresh generated id.
*Observable: pytest connects the same handle pair twice and asserts `len(edges) == 1`
plus the warning; a second test with `allow_duplicate_edges = True` asserts
`len(edges) == 2` with distinct ids.*

## 7. Non-Functional Requirements

### Performance
- Event payloads: change deltas only; hard cap 32 KB per payload (REQ-013).
- `on_viewport_change` debounce default 200 ms, configurable per instance (REQ-012).
- Target: 200-node / 300-edge graph pans and drags without WebSocket disconnect in the demo app.

### Compatibility
- Python 3.11+; Reflex latest stable at release time; `@xyflow/react` pinned `>=12,<13`.
- SSR decision documented in Tech Design (DD-001); behavior identical light/dark.

### Security / Supply chain
- Runtime deps MIT/Apache-2.0 only (Constitution Art. 2); CI runs Gitleaks + pip-audit.

### Maintainability
- Every MUST REQ covered by ≥1 test citing its ID (Constitution Art. 7).
- Docs include the v12 parity table (Constitution Art. 5).

## 8. Constraints and Dependencies

### Technical constraints
- Clean-room: public docs of `@xyflow/react` and Reflex only; prohibited sources per Constitution Art. 1.
- No own JS build step: local `.jsx` compiled by the Reflex pipeline via `rx.asset`.

### External dependencies

| Dependency | Type | License | Risk |
|---|---|---|---|
| Reflex | Runtime framework | Apache-2.0 | API churn between releases |
| @xyflow/react 12.x | JS runtime | MIT | Breaking minor changes |
| networkx | Runtime (layouts) | BSD-3 | Low — BSD is MIT-compatible; note in parity of Art. 2 wording |
| grandalf (optional) | Runtime (layered layout) | MIT/GPL dual — verify before adding | License check required |
| langgraph | Optional extra | MIT | Adapter only; isolated |

> Note: `networkx` is BSD-3-Clause. Constitution Art. 2 says "MIT or Apache-2.0";
> BSD-3 is equally permissive — the Tech Design must record this as an approved
> amendment or exception (constitution check).

## 9. User Stories

### Epic: Graph rendering from Python
**US-001:** As a Python app developer, I want to declare nodes and edges as Python
objects and see them rendered, so that I never write JavaScript. (REQ-001, 002, 003, 016, 017)

**US-002:** As a Python app developer, I want background, controls, and minimap out
of the box, so my editor looks complete with 3 lines. (REQ-004)

### Epic: Interactive editing
**US-003:** As a Python app developer, I want drags, connections, and deletions
reflected in my Python state without saturating the connection, so the app stays
responsive. (REQ-005–013, 030–032)

### Epic: Agent graphs
**US-004:** As an agentic-tooling developer, I want an `agent_node` with status
indicators driven from data, so I can show live agent execution. (REQ-020, 022)

**US-005:** As an agentic-tooling developer, I want `from_langgraph()` to convert my
compiled graph, so rendering takes one call. (REQ-035, 036)

### Epic: Layouts and customization
**US-006:** As a Python app developer, I want automatic layouts computed server-side,
so I don't position nodes by hand. (REQ-033, 034)

**US-007:** As an advanced developer, I want to register my own JSX node type, so I
can go beyond the built-ins. (REQ-025)

## 10. Wireframes / Mockups
Reference visuals: public reactflow.dev examples (overview, subflows, custom nodes).
Demo app pages double as living mockups: quickstart, registry showcase, agent graph,
layouts, escape hatch.

## 11. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Reflex wrapping API changes | Medium | High | Pin minimum Reflex version; CI against latest stable; thin adapter layer |
| xyflow 12.x breaking minor | Low | Medium | Pin `>=12,<13`; parity table per minor |
| Name confusion with `reflex-xy` / Enterprise "Reflex Flow" | Medium | Low | Constitution Art. 3; README disclaimer |
| Event payload edge cases saturate WS | Medium | High | Filtered event specs + debounce + 32 KB cap (REQ-005–013) |
| Clean-room contamination | Low | Critical | Constitution Art. 1 source list; PR checklist item |
| `grandalf` license ambiguity | Medium | Medium | Verify before adding; `networkx`-only fallback |

## 12. Estimated Timeline

| Phase | Deliverable |
|---|---|
| Phase 0 | Scaffolding, CI, LICENSE, specs/ in repo |
| Phase 1 | Layer 1 wrapper + events + demo app |
| Phase 2 | Layer 2 registry JSX |
| Phase 3 | Layer 3 FlowState + layouts |
| Phase 4 | LangGraph adapter, PyPI release, docs, gallery submission |

Durations are set in the Implementation Plan.

---

## Constitution check
- Art. 1/2 (clean-room, licensing): §8 constraints restate prohibited sources and the license chain; one exception flagged — `networkx` is BSD-3 (see §8 note), to be ratified as amendment.
- Art. 4 (Pythonic API): REQ-003, REQ-016, REQ-020 enforce snake_case/zero-JSX; escape hatch stays optional (REQ-025).
- Art. 5 (declared parity): §5.2 lists exclusions with reasons; parity table required by NFRs.
- Art. 6 (event performance): REQ-005–014 define filtered payloads, debounce, and the 32 KB cap.
- Art. 7/9 (testing, semver): every REQ names its observable; NFRs bind tests to REQ IDs.

## Change History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-08 | Ernesto Crespo | Initial version |

## Approvals

| Role | Name | Date | Status |
|---|---|---|---|
| Product/Owner | Ernesto Crespo | | ☐ Pending |
| Tech Lead | Ernesto Crespo | | ☐ Pending |
