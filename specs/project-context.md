# Project Context — Original SDD Prompt (English)

> This file preserves the founding prompt that generated the SDD spec kit in this
> directory, translated to English, so any agent session (Claude Code, Cowork, etc.)
> inherits the full project context. The normative artifacts are the specs
> themselves; on any conflict, `specs/constitution.md` and the approved specs win.

---

## Prompt — SDD for `reflex-react-flow` (open source React Flow v12 wrapper for Reflex)

Act as a senior software architect specialized in Reflex (Python) and the React
ecosystem. Use the spec-driven-design skill to fully plan, before writing any code,
the project described below. We work with the Spec-Driven Design/Development
methodology: specs are the primary artifact and the code will be implemented
afterwards, task by task, in Cowork sessions.

### 1. Project context

**Name:** `reflex-react-flow`
**Repo:** `github.com/ecrespo/reflex-react-flow`
**Import namespace:** `reflex_react_flow` (documented alias `import reflex_react_flow as rxf`)
**What it is:** an open source custom component for the Reflex framework that wraps
`@xyflow/react` v12 (React Flow), enabling node editors, flow charts, and
agent-graph visualizations from pure Python, without JavaScript.

**Motivation / niche:** no community React Flow wrapper for Reflex exists on PyPI.
The only complete wrapper ("Reflex Flow") lives inside `reflex-enterprise`, under
commercial terms. The official Reflex wrapping tutorial uses the legacy `reactflow`
(v11) package and covers ~10% of the API. The gap is real and the audience clear:
the Python community building agentic tooling (LangGraph, LightAgent) that needs to
visualize graphs without writing JavaScript.

**Naming (decided, do not reopen):** `reflex-react-flow` follows the ecosystem
precedent (`django-react-flow`, `funcnodes-react-flow`), avoids collision with the
official `reflex-xy` package (charts, by reflex-dev) and with the commercial name
"Reflex Flow" of Reflex Enterprise. Never use `reflex-flow` or `reflex-xyflow` in
code, docs, or metadata.

**Legal and license constraints (non-negotiable):**

- MIT license. In `pyproject.toml`: `license = "MIT"` and classifier
  `License :: OSI Approved :: MIT License`. `LICENSE` file at the root (MIT, year
  2026, Ernesto Crespo).
- Clean-room: implemented exclusively against the public API and documentation of
  `@xyflow/react` (MIT, reactflow.dev) and the public Reflex wrapping
  documentation. It is prohibited to read, consult, or derive code from
  `reflex-enterprise` or the xyflow Pro examples (advanced undo/redo, copy/paste,
  helper lines); if that functionality is needed, it is designed from scratch.
- No runtime dependencies on non-MIT/non-Apache-2.0 packages (Reflex is Apache
  2.0; `@xyflow/react` is MIT — clean chain).
- README with explicit attribution to xyflow/React Flow and a clarification that
  the project is not affiliated with xyflow GmbH or Pynecone, Inc.

**Distribution:** PyPI package created with `reflex component init` (name
`reflex-react-flow`), GitHub repo with topics `reflex`, `react-flow`, `xyflow`,
`python`, `node-editor`, `flow-chart`, `graph-visualization`, `diagrams`,
`langgraph`, `custom-component`. CI on GitHub Actions with the author's standard
quality tooling (Ruff, pre-commit, Gitleaks, pip-audit). Semver + changelog.

**Target stack:** Python 3.11+, Reflex (latest stable), `@xyflow/react` v12.x,
local JSX components packaged with Reflex's local-packages mechanism (`rx.asset`).
No own JS build step: local `.jsx` files are compiled by the Reflex pipeline.

### 2. Three-layer architecture (basis of the Tech Design)

**Layer 1 — Declarative surface (1:1 wrapper of the prop-driven API)**

- Full migration to `@xyflow/react` v12: named imports (not default), CSS
  `@xyflow/react/dist/style.css` via `_get_custom_code`.
- Main `ReactFlow` component with props: `nodes`, `edges`, `node_types`,
  `edge_types`, `color_mode` ("light"|"dark"|"system"), `fit_view`,
  `default_edge_options`, `connection_mode`, `snap_to_grid`, `snap_grid`,
  `min_zoom`, `max_zoom`, `translate_extent`, `node_extent`, `nodes_draggable`,
  `nodes_connectable`, `nodes_focusable`, `edges_focusable`,
  `elements_selectable`, `pan_on_drag`, `zoom_on_scroll`, `delete_key_code`,
  `viewport`/`default_viewport`.
- Wrapped plugin components: `Background` (dots/lines/cross variants), `Controls`,
  `MiniMap`, `Panel`, `NodeToolbar`, `NodeResizer`.
- Events as `EventHandler` with event specs that filter the payload (critical to
  avoid saturating the Reflex WebSocket): `on_nodes_change`, `on_edges_change`,
  `on_connect`, `on_connect_start`, `on_connect_end`, `on_node_click`,
  `on_node_double_click`, `on_node_drag_start`, `on_node_drag_stop`,
  `on_edge_click`, `on_pane_click`, `on_selection_change`, `on_nodes_delete`,
  `on_edges_delete`, `on_viewport_change` (with configurable debounce).
- Python data models: `Node`, `Edge`, `Viewport` as serializable
  dataclasses/TypedDicts, including subflows (`parent_id`, `extent="parent"`,
  `type="group"`), multiple handles, edge markers, labels, and edge types (bezier,
  step, smoothstep, straight).
- Decide and justify in the Tech Design: `rx.Component` or `rx.NoSSRComponent`?
  (v12 supports SSR with declared width/height; evaluate against the current
  Reflex pipeline).

**Layer 2 — Registry of parameterizable nodes (the differentiator)**

- One local `.jsx` file with 4–6 generic nodes whose content is 100% controlled
  from `node.data` in Python, without the user ever writing JSX:
  - `card_node`: icon, title, subtitle, status badge, handles configurable via data.
  - `agent_node`: oriented to agentic graphs — name, role, status
    (idle/running/done/error) with visual indicator, token/call counter.
  - `group_node`: container for subflows with a title.
  - `annotation_node`: free text / light markdown, no handles.
  - `io_node`: input/output with a single handle.
- Declarative handle configuration from Python: list of `{id, type, position}` in
  `node.data.handles`, rendered by the generic JSX.
- Documented escape hatch: the advanced user can register their own `.jsx` via
  `node_types`.

**Layer 3 — High-level Python API**

- `FlowState` (based on `rx.ComponentState`): encapsulates nodes/edges, operations
  `add_node`, `remove_node`, `add_edge`, `update_node_data`, `clear`, current
  selection, and application of `on_nodes_change`/`on_edges_change` changes
  (`apply_changes` pattern equivalent to the xyflow helpers, reimplemented in
  Python).
- Automatic server-side layout with `networkx` (and/or `grandalf`): hierarchical
  (dagre-like), force, circular, and layered layouts, computed in Python before
  sending the nodes. Zero layout JS.
- `from_langgraph(graph)` adapter (optional module, `[langgraph]` extra): consumes
  a compiled LangGraph `StateGraph` and produces nodes/edges with `agent_node`,
  ready to render. This adapter is a candidate for the final phase or for a
  sibling package `reflex-langgraph-flow`; decide in the Implementation Plan.

### 3. SDD instructions (how to work)

- Rigor level: `spec-anchored`. Specs live in the repo under `specs/`, versioned;
  later changes via Delta Specs in `changes/`.
- Depth: treat as a new project per the skill's table → Constitution first, then
  the 5 documents (PRD with EARS, API Spec, Tech Design, Data Model,
  Implementation Plan), then Tasks, and the Analyze gate before implementing.
- One artifact per exchange. Generate, wait for explicit review/approval, and only
  then continue with the next. Do not generate the whole chain at once.
- Order: `constitution.md` → `prd/reflex-react-flow.md` →
  `api/reflex-react-flow-api-v1.md` → `technical/reflex-react-flow-architecture.md`
  → `data-model/reflex-react-flow-schema.md` → `plans/reflex-react-flow-phase-1.md`
  → `tasks/reflex-react-flow-tasks.md` → Analyze.
- Traceability: every MUST requirement with ID `REQ-NNN`; every task cites its
  REQ; every EARS criterion names its observable, verifiable outcome (no "EARS
  theater").
- After finishing the Constitution, provide the snippet to reference it from the
  repo's `CLAUDE.md`/`AGENTS.md`, so every agent session inherits the principles.

### Artifact-specific guidance

**Constitution** — capture as principles: strict clean-room (with the list of
prohibited sources), MIT license and clean dependency chain (only MIT/Apache-2.0 at
runtime), decided naming (`reflex-react-flow`; `reflex-flow`/`reflex-xyflow`
forbidden), Pythonic API first (snake_case, dataclasses, zero mandatory JSX for 90%
of cases), declared parity with v12 (document what is NOT covered and why), event
channel performance (every high-frequency event must have a filtered payload spec +
debounce strategy), mandatory testing (pytest + integration tests with a Reflex demo
app), and semver with changelog.

**PRD** — personas: (1) Python dev visualizing pipelines/graphs without touching
JS, (2) agentic-tooling dev who wants to render LangGraph, (3) advanced dev who
needs the JSX escape hatch. EARS criteria per layer; explicitly include undesired
behaviors (IF the `on_nodes_change` payload exceeds N KB, THEN...; IF a `node_type`
does not exist in the registry, THEN...).

**API Spec** — here the "contract" is the package's public Python API: signature of
every component (`react_flow`, `background`, `controls`, `mini_map`, `panel`,
`node_toolbar`, `node_resizer`), `Node`/`Edge`/`Viewport` models, `FlowState`
signature, layouts module, and the registry contract (exact `node.data` schema
consumed by each generic node). Versioned v1.

**Tech Design** — decisions with alternatives and trade-offs: SSR vs NoSSR; event
serialization (Reflex event specs, which fields travel); debounce strategy; local
JSX packaging with `rx.asset(shared=True)`; how wrapped components are tested (demo
app + Playwright vs unit); risks (Reflex API changes, xyflow 12.x breaking changes,
name collision with the official `reflex-xy` and Enterprise's "Reflex Flow") and
mitigations.

**Data Model** — there is no database: the model is the
`Node`/`Edge`/`Viewport`/`HandleConfig`/`NodeChange`/`EdgeChange` structures and the
JSON schema of `node.data` per registry node type. Specify it with the same rigor as
a DB schema (types, required, defaults, validation).

**Implementation Plan** — phases aligned to the layers: Phase 0 scaffolding
(`reflex component init --package-name reflex-react-flow`, MIT LICENSE, CI,
pre-commit, specs/ structure, README with attribution); Phase 1 = Layer 1 (wrapper +
events + demo app); Phase 2 = Layer 2 (JSX registry); Phase 3 = Layer 3 (FlowState +
layouts); Phase 4 = LangGraph adapter + PyPI publication + docs + Reflex
custom-components gallery. Each phase with a verifiable exit criterion.

---

## Resulting spec kit (index)

| Artifact | File |
|---|---|
| Constitution | `specs/constitution.md` |
| PRD (EARS, REQ-NNN) | `specs/prd/reflex-react-flow.md` |
| API Spec v1 | `specs/api/reflex-react-flow-api-v1.md` |
| Tech Design | `specs/technical/reflex-react-flow-architecture.md` |
| Data Model | `specs/data-model/reflex-react-flow-schema.md` |
| Implementation Plan | `specs/plans/reflex-react-flow-phase-1.md` |
| Tasks (T-001..T-023) | `specs/tasks/reflex-react-flow-tasks.md` |
| Analyze report | `specs/analyze-report.md` |
