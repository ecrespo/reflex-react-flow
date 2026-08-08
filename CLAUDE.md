# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`reflex-react-flow` — an MIT-licensed Reflex custom component wrapping `@xyflow/react` v12
(React Flow), so Python developers build node editors, flow charts, and agent-graph
visualizations without writing JavaScript. PyPI package `reflex-react-flow`, import
namespace `reflex_react_flow` (documented alias `import reflex_react_flow as rxf`).

**Current state: specs only.** `specs/` holds a complete, approved-pending SDD kit; no
Python package, `pyproject.toml`, or tests exist yet. Phase 0 (scaffolding) has not been
executed. Do not assume any file under `custom_components/` exists — check first.

## Governance: read the specs before writing code

`specs/constitution.md` is normative and overrides ordinary judgment. Every artifact
(PRD, API Spec, Tech Design, Plan, Tasks) must end with a "Constitution check" section.

Non-negotiables that will bite you if forgotten:

- **Art. 1 — clean room.** Implement *only* against public `@xyflow/react` docs
  (reactflow.dev) and public Reflex wrapping docs. Never read, consult, or derive from
  `reflex-enterprise` / "Reflex Flow", or the xyflow **Pro** examples (advanced undo/redo,
  copy/paste, helper lines). Overlapping features are designed from scratch.
- **Art. 3 — naming is settled.** Only `reflex-react-flow` / `reflex_react_flow`. The
  strings `reflex-flow` and `reflex-xyflow` must never appear in code, docs, or metadata.
- **Art. 4 — no React idioms leak.** Public API is snake_case; camelCase translation
  happens only at the wrapper boundary in `components/`.
- **Art. 6 — no unfiltered events.** Every event handler needs a JS-side event spec that
  emits only whitelisted delta fields. Never serialize whole node/edge objects.
- **Art. 7 — every MUST REQ needs a test citing its `REQ-NNN` id** (in the test docstring)
  before its task closes.
- **Art. 2 — runtime deps must be MIT/Apache-2.0** (see Blocking issues below).

Spec kit index: `constitution.md` → `prd/` → `api/reflex-react-flow-api-v1.md` →
`technical/reflex-react-flow-architecture.md` → `data-model/` → `plans/` → `tasks/` →
`analyze-report.md`. `specs/project-context.md` preserves the founding prompt.

### Blocking issues before Phase 0 closes

`specs/analyze-report.md` verdict is "READY TO IMPLEMENT after resolving A-01 and A-02":

- **A-01**: `networkx` is BSD-3, which Art. 2 (MIT/Apache-2.0 only) does not permit. The
  amendment to "MIT, Apache-2.0, or BSD-permissive" is flagged but **not ratified** — add
  it to the Constitution amendments table.
- **A-02**: `card_node.data.icon` names no icon set. Pin one (with its license) in Data
  Model §4.1 before implementing the registry (T-013).

## Working method (SDD, spec-anchored)

- Work task by task from `specs/tasks/reflex-react-flow-tasks.md`; update its checkboxes
  (`[ ]` / `[~]` / `[x] {date}` / `[!]`) as you go — that file is the resume point for any
  session.
- Each task lists **What / REQ / Files / Depends on / Done**. The `Done` line is a literal
  command or observation; satisfy it verbatim before marking done.
- `[P]` tasks are parallelizable (no shared files, no dependency).
- **If implementation reveals a spec error: stop, fix the spec (or open a Delta Spec in
  `changes/`), then continue.** Never let code silently diverge from a spec.

## Commands

`uv` is the project manager (Tech Design DD-008); all local and CI commands go through it.
These become valid after T-001 scaffolding:

```bash
uv sync                                   # create/refresh env from uv.lock
uv run python -c "import reflex_react_flow"   # Phase 0 exit gate
uv run pytest                             # full suite
uv run pytest tests/unit/test_models.py   # one file
uv run pytest -k "test_name"              # one test
uv run pytest tests/integration           # Playwright suite (needs flow_demo running)
uv run ruff check . && uv run ruff format .
uv run pre-commit run --all-files         # Ruff + Gitleaks + pip-audit gate
uv run reflex run                         # from flow_demo/ — demo app / integration target
uv build && uv publish                    # release (Phase 4, via CI trusted publishing)
```

`pip install reflex-react-flow` is the end-user path; `uv` is dev-side only.

Traceability check used by phase gates: `grep -r "REQ-0" tests/` must map every MUST REQ.

## Architecture (three layers)

Target layout — `custom_components/reflex_react_flow/`:

**Layer 1 — declarative wrapper** (`components/react_flow.py`, `components/plugins.py`,
`models.py`, `assets/event_utils.js`). Main canvas is `rx.NoSSRComponent` (DD-001: SSR
buys nothing for a behind-login canvas and risks hydration bugs). v12 named imports plus
`@xyflow/react/dist/style.css` injected via `_get_custom_code`. Plugin components:
`background`, `controls`, `mini_map`, `panel`, `node_toolbar`, `node_resizer`.

The event channel is the load-bearing design (DD-002/003). ~15 event handlers each declare
a Reflex event spec whose JS extracts only the fields in API Spec §5, sharing helpers from
`assets/event_utils.js`: field whitelisting, a 32 KB payload cap (truncate + namespaced
`[reflex-react-flow]` console warning), and a trailing-edge debounce factory. Defaults:
`viewport_debounce_ms=200`, `max_event_payload_kb=32`. Drag movement is **not** streamed —
only `drag_start`/`drag_stop` plus React Flow's batched position changes on drop.

**Layer 2 — node registry** (`assets/registry.jsx`, one file, shipped via
`rx.asset(path, shared=True)` — no JS build step of ours). Five generic components —
`CardNode`, `AgentNode`, `GroupNode`, `AnnotationNode`, `IONode` — rendered 100% from
`node.data`, with handles driven by `data.handles`. The `node.data` schemas are public API
(Data Model §4); changing them needs a Delta Spec. Users may register their own `.jsx` via
`node_types` (documented escape hatch, not the default path).

**Layer 3 — high-level Python** (`state.py`, `changes.py`, `layouts.py`,
`adapters/langgraph.py`). `FlowState` extends `rx.ComponentState`. `changes.py` and
`layouts.py` are **pure functions** — testable with no Reflex runtime. Layouts
(hierarchical, force, circular, layered) run server-side on `networkx`; zero layout JS.
`from_langgraph` sits behind the `[langgraph]` extra with an ImportError guard carrying an
install hint (REQ-036).

Round trip: browser event → JS spec filters to a delta → WS → `FlowState.on_nodes_change`
→ `apply_node_changes` mutates state → Reflex re-pushes the `nodes` prop → React Flow
reconciles without re-mounting.

## Error-handling policy (per layer)

| Layer | Policy |
|---|---|
| Model construction | raise `ValueError` naming the offending field (REQ-016) |
| Event application | **never raise** — skip the change and `warnings.warn` (REQ-032) |
| Browser / JSX | namespaced console warnings only; never throw into React |

Unknown node type → React Flow default node + console warning (REQ-023). Cyclic graph in a
hierarchical layout → break the cycle + warn (REQ-034).

## Security constraints

`node.data` strings (labels, annotation "light markdown") render as text nodes or through a
whitelist renderer (bold/italic/code) — **never** `dangerouslySetInnerHTML`. Event specs
whitelist fields; Python models validate types before mutating state.

## Documentation obligations

- README carries xyflow/React Flow attribution and an explicit non-affiliation disclaimer
  re: xyflow GmbH and Pynecone, Inc. (Art. 2).
- Docs maintain a **v12 parity table** stating which features are covered and which are out
  of scope with a one-line reason each — silent partial coverage must not ship (Art. 5).
- Semver + `CHANGELOG.md` (Keep a Changelog) on every release; breaking public-API changes
  need a major version preceded by a Delta Spec in `changes/` (Art. 9).
