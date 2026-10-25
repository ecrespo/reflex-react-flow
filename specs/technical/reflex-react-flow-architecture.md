# reflex-react-flow — Technical Design Document

## Metadata

| Field | Value |
|---|---|
| **Author** | Ernesto Crespo |
| **Status** | `DRAFT` |
| **Version** | 1.0 |
| **Date** | 2026-08-08 |
| **Related PRD** | [specs/prd/reflex-react-flow.md](../prd/reflex-react-flow.md) |
| **Related API Spec** | [specs/api/reflex-react-flow-api-v1.md](../api/reflex-react-flow-api-v1.md) |
| **Constitution** | [specs/constitution.md](../constitution.md) |

---

## 1. Context

We are building a Reflex custom component that wraps `@xyflow/react` v12. Reflex
components are Python classes that compile to React code; wrapped third-party
components declare their npm dependency (`library`), tag, props, and event
handlers, and Reflex's build pipeline bundles everything. Two technically sensitive
areas dominate the design: (a) the event channel — React Flow fires high-frequency
callbacks whose raw payloads (full node objects, React synthetic events) would
saturate the Reflex WebSocket, so every event needs a JS-side event spec that filters
the payload before serialization; and (b) the generic-node registry — local `.jsx`
assets compiled by Reflex's pipeline via `rx.asset(shared=True)`, so users get rich
node types without a JS build step of ours or theirs.

The implementation is strictly clean-room (Constitution Art. 1): only public
reactflow.dev docs and public Reflex wrapping docs are inputs.

## 2. Technical Objectives

- **Correctness:** Python state and canvas state converge after every event round-trip; `apply_node_changes` semantics match documented xyflow behavior.
- **Performance:** 200-node graph interactable without WS disconnect; every high-frequency event has a written payload spec (Art. 6); viewport debounce default 200 ms; payload cap 32 KB.
- **Maintainability:** MUST-REQ test coverage 100%; wrapper prop table generated/verified by unit tests; single `.jsx` asset for the registry.
- **Portability:** no own JS build step; works with `reflex component init` project layout and the Reflex local-packages mechanism.

## 3. Proposed Architecture

### 3.1 High-level diagram

```
┌────────────────────────── Python (user app) ──────────────────────────┐
│  FlowState (rx.ComponentState)   layouts (networkx)   from_langgraph  │
│        │ nodes/edges (JSON)              ▲                            │
└────────┼─────────────────────────────────┴────────────────────────────┘
         ▼ props (serialized)                     ▲ events (filtered)
┌─────────────────────── Reflex wrapper (Layer 1) ──────────────────────┐
│ ReactFlowLib(rx.NoSSRComponent)  · props map · event specs (JS)       │
│ react_flow / background / controls / mini_map / panel / node_toolbar  │
│ / node_resizer      · CSS injection · debounce/cap hooks              │
└────────┼──────────────────────────────────────────────────────────────┘
         ▼ compiled React
┌──────────────────── Browser (@xyflow/react v12) ──────────────────────┐
│ <ReactFlow nodeTypes={registry}>  Background Controls MiniMap …       │
│ registry.jsx (rx.asset, shared=True): CardNode AgentNode GroupNode    │
│ AnnotationNode IONode  ← rendered 100% from node.data                 │
└───────────────────────────────────────────────────────────────────────┘
```

### 3.2 Components

| Component | Technology | Responsibility |
|---|---|---|
| `components/react_flow.py` | Reflex component classes | Main canvas wrapper, prop translation, event specs |
| `components/plugins.py` | Reflex component classes | Background, Controls, MiniMap, Panel, NodeToolbar, NodeResizer |
| `models.py` | dataclasses / TypedDicts | `Node`, `Edge`, `Viewport`, `HandleConfig`, `EdgeMarker`, change/connection payloads |
| `state.py` | `rx.ComponentState` | `FlowState`, change application |
| `changes.py` | pure Python | `apply_node_changes` / `apply_edge_changes` |
| `layouts.py` | Python + networkx | 4 layout algorithms |
| `adapters/langgraph.py` | Python (optional import) | `from_langgraph` |
| `assets/registry.jsx` | JSX (local asset) | 5 generic node components + registry export |
| `assets/event_utils.js` | JS (local asset) | payload filter/truncate/debounce helpers used by event specs |
| demo app `flow_demo/` | Reflex app | living docs + integration-test target |

### 3.3 Data flow

**Flow: user drags a node**

```
1. Browser: ReactFlow fires onNodesChange([{id, type:"position", position, dragging}])
2. Event spec (JS): filters to delta fields, enforces 32 KB cap (truncate+warn)
3. Reflex WS → FlowState.on_nodes_change(changes)
4. apply_node_changes mutates state.nodes (unknown ids: skip + warn)
5. Reflex re-renders: nodes prop → canvas (React Flow reconciles, no re-mount)
```

**Flow: server-side layout**

```
1. User calls FlowState.apply_layout("hierarchical")
2. layouts.layout_hierarchical builds networkx DiGraph from nodes/edges
3. Positions computed in Python (cycle-break if needed, REQ-034)
4. state.nodes replaced with repositioned copies → single props update
```

**Error/compensation flow**

```
- Event for unknown id → skipped + warnings.warn (REQ-032); state never raises mid-event
- Payload > cap → truncated in JS before send; console warning (REQ-013)
- Unknown node type → React Flow default node + console warning (REQ-023)
```

**WebSocket reconnect (A-08).** The convergence claim in §2 assumes a live channel;
connection lifecycle is **Reflex's responsibility, not the wrapper's**. Events emitted
while the socket is down are lost by design — we do not queue them. On reconnect Reflex
re-pushes the full `nodes`/`edges` props from server state, so the canvas is restored to
the server's view; any purely client-side interaction that never reached the server
(e.g. a drag completed mid-outage) is discarded. Server state is the single source of
truth: the wrapper holds no authoritative client-side graph state.

## 4. Design Decisions

### DD-001: `rx.NoSSRComponent` vs `rx.Component`

- **Decision:** Wrap the main canvas as `rx.NoSSRComponent` for v1.
- **Context:** React Flow v12 supports SSR when explicit `width`/`height` are set on nodes, but full-canvas SSR needs measured DOM and window; Reflex prerenders components server-side by default.
- **Alternatives:**

| Option | Pros | Cons |
|---|---|---|
| **NoSSRComponent (chosen)** | No hydration mismatch; matches how most canvas libs are wrapped in Reflex; simplest to certify | Blank placeholder flash on first paint; no SEO of graph content (irrelevant here) |
| Component (SSR) | v12 nominally supports SSR with declared dimensions; faster first paint | Requires width/height on every node; fragile against Reflex prerender pipeline; hydration bugs are costly to debug |

- **Justification:** graph editors are behind-login interactive surfaces; SSR yields no user value here and carries the project's largest debugging risk.
- **Consequences:** revisit as a Delta Spec if Reflex's SSR story or user demand changes; `width`/`height` props still supported on `Node` so an SSR variant remains possible.

### DD-002: Event serialization — JS event specs with delta filtering

- **Decision:** Every event handler declares a Reflex event spec whose JS extracts only the fields in API Spec §5; shared helpers live in `assets/event_utils.js`.
- **Alternatives:**

| Option | Pros | Cons |
|---|---|---|
| **JS-side filtering via event specs (chosen)** | Payload bounded before hitting WS; matches Art. 6; one place to test | Small JS surface to maintain |
| Send raw payloads, filter in Python | No JS | WS saturated by then — defeats the purpose |
| Lambda-only specs per event | No shared file | Duplicated logic across 15 events; cap/debounce impossible to share |

- **Justification:** the WebSocket is the scarce resource; filtering must happen before serialization.
- **Consequences:** event payload shapes are a tested public contract; changes require Delta Specs.

### DD-003: Debounce strategy

- **Decision:** Debounce `on_viewport_change` in JS (trailing edge, default 200 ms, prop-configurable). Drag movement is *not* streamed: only `drag_start`/`drag_stop` plus React Flow's batched `position` changes on drop (`onNodesChange` fires during drag only for the dragged node; the spec coalesces to ≤ 1 event per animation frame and the cap bounds the worst case).
- **Alternatives considered:** throttle server-side (too late), stream positions at 60 Hz (saturates), no debounce (violates Art. 6).
- **Consequences:** REQ-009/REQ-012 are testable by counting server events.

### DD-004: JSX packaging via `rx.asset(shared=True)`

- **Decision:** `registry.jsx` and `event_utils.js` ship inside the Python package and are exposed with `rx.asset(path, shared=True)`; components import them via the `$/public` (shared asset) path; Reflex's compiler bundles them.
- **Alternatives:**

| Option | Pros | Cons |
|---|---|---|
| **rx.asset(shared=True) (chosen)** | Official local-packages mechanism; zero build step; assets versioned with the wheel | Coupled to Reflex asset path conventions |
| Publish companion npm package | Independent versioning | An npm publish pipeline for a Python-first project; overkill |
| Inline JS strings in Python | Single file | Unreadable, unlintable, no syntax checks |

- **Consequences:** a Reflex change to asset handling is a tracked risk (R-01).

### DD-005: Registry as one `.jsx` file with data-driven components

- **Decision:** One `registry.jsx` exporting the 5 node components and a `defaultNodeTypes` map; every visual aspect read from `node.data` with defaults (REQ-024); handles rendered from `data.handles` (REQ-021).
- **Justification:** single asset keeps the escape hatch story symmetric (users register their own types into the same `node_types` dict) and minimizes JS surface.
- **Consequences:** the `node.data` schemas are public API (Data Model §4).

### DD-006: Layout engine — networkx only for v1

- **Decision:** Implement all 4 layouts on `networkx` (BSD-3). `grandalf` deferred until its licensing is verified (PRD §8 risk).
- **Justification:** networkx covers layered/hierarchical (topological generations), force (spring), circular natively; one dependency, permissive license.
- **Consequences:** hierarchical quality below true dagre for dense graphs; acceptable for v1, revisit via Delta.

### DD-007: LangGraph adapter stays in-package as optional extra

- **Decision:** `adapters/langgraph.py` behind `[langgraph]` extra for v1 (not a sibling package).
- **Justification:** one small module; a separate package before demand is proven adds release overhead. Split later via Delta Spec if it grows (PRD §5.3).

### DD-008: `uv` as package and project manager

- **Decision:** Use `uv` for all dependency and project management: `pyproject.toml` as the single source of truth, `uv.lock` committed, `uv sync` for env setup, `uv run` for every local/CI command (pytest, ruff, reflex run), `uv build`/`uv publish` for the PyPI release, and `uv python` to pin interpreter versions in the CI matrix (3.11/3.12).
- **Alternatives:**

| Option | Pros | Cons |
|---|---|---|
| **uv (chosen)** | Fast, lockfile-based reproducibility; single tool for venv/deps/build/publish; first-class CI caching | Younger tool; team must have it installed |
| pip + venv | Ubiquitous | No lockfile; slower CI; manual venv management |
| Poetry | Mature lockfile workflow | Slower; second build backend; overlaps with `reflex component init` layout |

- **Justification:** reproducible installs (lockfile) directly serve Constitution Art. 8 (supply-chain hygiene: `pip-audit` runs against a pinned resolution) and keep CI fast for the Playwright matrix.
- **Consequences:** all docs and task Done criteria use `uv run …` commands; contributors need `uv` ≥ latest stable installed; `pip install reflex-react-flow` remains the end-user install path (uv is a dev-side tool only).

## 5. Patterns and Conventions

### 5.1 Code structure

```
reflex-react-flow/
├── pyproject.toml               # MIT, classifiers, [langgraph] extra (managed with uv)
├── uv.lock                      # committed lockfile (DD-008)
├── LICENSE                      # MIT © 2026 Ernesto Crespo
├── README.md                    # attribution + non-affiliation (Art. 2)
├── CHANGELOG.md
├── specs/ …                     # this spec kit
├── custom_components/
│   └── reflex_react_flow/
│       ├── __init__.py          # public exports (API Spec §1)
│       ├── components/
│       │   ├── react_flow.py
│       │   └── plugins.py
│       ├── models.py
│       ├── changes.py
│       ├── state.py
│       ├── layouts.py
│       ├── adapters/langgraph.py
│       └── assets/
│           ├── registry.jsx
│           └── event_utils.js
├── flow_demo/                   # demo app (docs + integration target)
└── tests/
    ├── unit/                    # models, changes, layouts, prop translation
    └── integration/             # Playwright against flow_demo
```

### 5.2 Patterns

| Pattern | Where | Why |
|---|---|---|
| Boundary translation (Adapter) | components/* | snake_case→camelCase in one place (Art. 4) |
| Pure functions | changes.py, layouts.py | Testable without Reflex runtime |
| Optional import guard | adapters/langgraph.py | REQ-036 ImportError with hint |
| Data-driven rendering | registry.jsx | Zero user JSX (Art. 4) |
| Strategy + Registry | layouts.py | 4 interchangeable layout algorithms behind one signature; `apply_layout(algorithm=...)` resolves by name — adding a 5th layout touches no caller (OCP) |
| Command / dispatch table | changes.py | One handler per `NodeChange.type`; `apply_*_changes` dispatches, never an if-elif ladder that grows per change type (OCP) |
| Adapter | adapters/langgraph.py | Foreign graph shape → our `Node`/`Edge` model; the adapter is the only module that knows LangGraph exists (DIP) |
| Factory | models.py `from_dict` | Single construction+validation path for every entry point (DRY) |
| Template Method | registry.jsx node shells | Shared node chrome (border, handles, selection ring) defined once; each type fills the body slot (DRY) |

### 5.2.1 Engineering principles (normative)

**SOLID.**
- *SRP* — one reason to change per module: `models.py` shape+validation, `changes.py`
  change semantics, `layouts.py` geometry, `state.py` orchestration, `components/*`
  Python↔React translation. A module that both validates and lays out is a defect.
- *OCP* — new layout algorithms, change types, registry node types, and event specs are
  added by registering into a table, never by editing a conditional chain.
- *LSP* — every `layout_*` function is substitutable behind the layouts signature
  (`(nodes, edges, **opts) -> list[Node]`, pure, non-mutating); every registry node
  honors the same `data`-driven contract, so types are swappable in `node_types`.
- *ISP* — `FlowState` exposes narrow, intention-revealing operations (`add_node`,
  `update_node_data`, …) rather than a god-object `mutate(**kwargs)`; event handlers are
  independent optional props, so a consumer wires only the events it wants.
- *DIP* — `state.py` depends on the *pure helper functions* (`apply_node_changes`,
  `layouts.*`), not the reverse; `changes.py`/`layouts.py` import nothing from Reflex, so
  Layer 3 logic is testable and reusable without the framework.

**DRY.** Each fact lives once: the prop translation table is the single source for
snake→camel (tests assert against it, docs generate from it); payload filtering/cap/
debounce live only in `assets/event_utils.js` and are shared by all ~15 event specs;
node chrome lives in one JSX shell; validation lives only in the model constructors.
Duplicated knowledge is the defect, not duplicated characters — three similar-looking
event specs that encode three genuinely different payloads are not a DRY violation.

*Tension with Art. 4:* where a Pythonic API and a pattern conflict, the Pythonic API
wins — we do not introduce abstract base classes, dependency-injection containers, or
factories that the user must see. Patterns stay behind the public surface.

### 5.3 Error handling

| Layer | Policy |
|---|---|
| Model construction | `ValueError`, field named (REQ-016) |
| Event application | never raise; skip + `warnings.warn` (REQ-032) |
| Browser | console warnings only (REQ-013/023); never throw into React |

## 6. Security

| Vector | Mitigation |
|---|---|
| XSS via `node.data` strings (labels, annotation markdown) | JSX renders as text nodes; annotation "light markdown" uses a whitelist renderer (bold/italic/code), never `dangerouslySetInnerHTML` |
| Malicious payloads on event channel | Event specs whitelist fields; Python models validate types before state mutation |
| Supply chain | Runtime deps MIT/Apache/BSD-permissive only; Gitleaks + pip-audit in CI (Art. 8); reproducible resolution via committed `uv.lock` (DD-008) |

## 7. Observability

Library context (no server metrics of our own):
- Python: `warnings.warn` with `ReflexReactFlowWarning` category for skips/cycle-breaks — filterable by users.
- Browser: namespaced console warnings `[reflex-react-flow] …` (REQ-013/023).
- Demo app: debug panel page showing live event counts/sizes (also used by perf tests).

## 8. Testing Strategy

| Level | Target | Tools | Covers |
|---|---|---|---|
| Unit (Python) | >90% of models/changes/layouts | pytest | REQ-016, 030–034, 036; prop translation table (REQ-003) |
| Unit (component render) | serialized component tree | pytest + Reflex render harness | props/camelCase mapping, CSS injection (REQ-001), event spec JS strings |
| Integration (browser) | critical flows on `flow_demo` | Playwright (pytest-playwright) | REQ-002, 004, 005–015, 017–025 |
| Performance | event-channel budget | Playwright + debug panel | 200-node drag/pan budget; REQ-012/013 counts |

Decision (component testing): wrapped components are verified at two cheap levels
(rendered-tree unit tests + Playwright on the demo app); no jsdom/JS unit tests — the
JS surface is intentionally too small to justify a JS test toolchain.

## 9. Rollout

- v0.1.0 on PyPI after Phase 4 gate (plan doc); pre-releases `0.0.x` from Phase 1 for early feedback.
- Compatibility: pin `reflex >=` (version fixed at Phase 0), `@xyflow/react >=12,<13`.
- Rollback: PyPI yank + patch release; no server infra.

## 10. Risks and Mitigations

| ID | Risk | Prob. | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | Reflex changes wrapping/asset APIs | Med | High | Thin boundary layer; CI on latest Reflex; pin minimum |
| R-02 | xyflow 12.x breaking minor | Low | Med | Pin `<13`; parity table per minor; renovate PRs |
| R-03 | Name collision confusion (`reflex-xy`, "Reflex Flow") | Med | Low | Art. 3 + README disclaimer |
| R-04 | Clean-room contamination | Low | Critical | Art. 1 prohibited-source list; PR checklist |
| R-05 | Event channel saturation edge cases | Med | High | DD-002/003; perf test in CI |
| R-06 | grandalf license | Med | Med | DD-006: networkx only |

## 11. Open Questions

- [x] **Exact minimum Reflex version** → `reflex>=0.9.8` (latest stable at Phase 0; fixed in `pyproject.toml`, T-001).
  **Raised to `reflex>=0.10.0` on 2026-10-25** (0.0.2 release); re-verified in §12.2.
- [x] **`ReflexReactFlowWarning` vs stdlib `UserWarning`** → define
  `ReflexReactFlowWarning(UserWarning)` in `custom_components/reflex_react_flow/warnings.py`.
  Subclassing `UserWarning` keeps our warnings **visible by default** (unlike
  `DeprecationWarning`, which is hidden outside `__main__`), while the dedicated category
  lets users silence *only* this package —
  `warnings.filterwarnings("ignore", category=ReflexReactFlowWarning)` — without going
  deaf to every `UserWarning` in their app. Used by REQ-032 (unknown id), REQ-034
  (cycle-break), REQ-037 (duplicate connection) and INV-03.
- [x] **Whether `panel` children need a slot wrapper** → **no wrapper needed.** Verified in
  the T-005 spike: `Panel.create(rx.text("hi"), position="top-left")` passes children
  through natively and renders as a child of the canvas.

## 12. T-005 spike findings (verified against Reflex 0.9.8)

All five load-bearing assumptions were exercised against the real framework, not inferred
from docs. Findings that change how Layer 1 is written:

| # | Assumption | Verdict | Evidence / consequence |
|---|---|---|---|
| 1 | `rx.NoSSRComponent` can wrap the canvas (DD-001) | **Holds** | Emits `ClientSide(...)` from `$/utils/context`; no SSR path taken |
| 2 | v12 **named** imports, not default (REQ-001) | **Holds** | Generated: `const ReactFlow = ClientSide(() => import('@xyflow/react').then((mod) => mod.ReactFlow))` — resolves `mod.ReactFlow`, never `mod.default` |
| 3 | CSS injectable without user action (REQ-001) | **Holds** | `add_custom_code()` returning `import "@xyflow/react/dist/style.css";` lands in the compiled custom code |
| 4 | Event specs can filter payload **in JS** (DD-002) | **Holds — critical** | A spec returning `Var("rrfFilterNodeChanges(changes, 32)")` compiles to `onNodesChange: ((_changes) => addEvents([ReflexEvent(..., {changes: rrfFilterNodeChanges(_changes, 32)})], ...))`. The filter runs **before** the payload is serialized into the event, which is precisely the Art. 6 contract |
| 5 | `rx.asset(path, shared=True)` (DD-004) | **Holds** | Returns `/external/<module>/<file>?v=<hash>`; content-hashed, so registry/JS assets are cache-busted per build |

**Finding S-01 (affects T-006).** Reflex already performs snake_case→camelCase
translation on props automatically (`fit_view`→`fitView`, `snap_grid`→`snapGrid`,
`min_zoom`→`minZoom`). Art. 4 is therefore satisfied by the framework for the regular
case, and the wrapper must **not** hand-roll a second translation layer (that would be
the DRY violation §5.2.1 warns about). The REQ-003 prop-table test remains mandatory:
it now guards against a Reflex-side regression and pins the handful of props whose React
name is *not* the naive camelisation. Only those exceptions get an explicit override.

**Finding S-02 (affects T-006).** The npm dependency is declared inline in the `library`
string as `"@xyflow/react@^12.3.5"`; the caret range resolves to `>=12.3.5 <13`, which
satisfies the `>=12,<13` pin required by §9 without a separate `lib_dependencies` entry.

### 12.1 Findings from the T-012 browser suite

**Finding S-03 — controlled-state feedback loop (binding constraint on T-017).**
A handler that reassigns `nodes` on *every* `on_nodes_change` batch — including batches
where nothing applied, such as a `dimensions` measurement — creates an unbounded loop:
new list → new prop → React Flow re-measures → new `dimensions` change → handler fires
again. Measured at **~60 events/second** in the demo, which saturates precisely the
channel Art. 6 exists to protect, and no amount of payload filtering fixes it because
each individual payload is small and legal.

`apply_node_changes` / `apply_edge_changes` (T-017) **MUST therefore be no-ops when no
change applies**, returning the *same* list object rather than an equal copy, and
`FlowState` must not assign to `nodes`/`edges` when the helper reports no mutation. This
is a correctness requirement, not an optimisation. It is covered by REQ-031's task and
must have a regression test: "a batch of dimensions-only changes leaves state identical
and triggers no re-push".

**Finding S-04 — the canvas needs a sized parent.** React Flow's stylesheet declares
`.react-flow { height: 100% }` and is injected after component styles, so a height set
on the canvas itself loses on source order and the canvas collapses (observed: 2 px).
Its documented contract is that the *parent* carries the dimensions. The demo wraps the
canvas in a sized box accordingly. **Open item for the API Spec:** a Python user will
naturally write `react_flow(..., height="600px")` and get a broken canvas, so v1 docs
must state the sized-parent rule prominently (T-022), and a future Delta may add
first-class `width`/`height` props that emit the wrapper themselves.

### 12.2 Re-verification against Reflex 0.10.0 (2026-10-25)

The minimum was raised to `reflex>=0.10.0`. The five §12 assumptions still hold — the
unit suite and the T-012 browser suite pass unchanged against 0.10.0 — with these
observations:

- **Auto-memoized components.** Reflex 0.10 compiles stateful components into shared
  memo modules (`.web/app_components/`). Our `add_custom_code()` output and the
  `_render()` event-chain rewrites (viewport debounce) land there intact; nothing in the
  wrapper had to change for it.
- **Radix Themes must be declared.** Implicit Radix Themes enablement is deprecated
  (removed in 1.0). The demo now lists `rx.plugins.RadixThemesPlugin()` in `rxconfig.py`.
  The package itself uses no Radix component, so users are unaffected.
- **Hot reload scope.** `reflex run` reloads the app package only; edits under
  `custom_components/` need a restart. A stale server makes the browser suite appear to
  test code it is not running.

**Finding S-05 — literal props re-render loop (wrapper-level, fixed).** S-03 described
the loop for state write-back; the same loop occurs with *no* state write-back to
`nodes` at all whenever the canvas receives a **literal** list. Reflex inlines a literal
`nodes=[...]` as an array expression in the render function, so every render — including
the one triggered by any handled event — hands React Flow a new array. React Flow treats
it as new nodes: it re-measures them (`dimensions` changes → `on_nodes_change`) and
re-fires `onSelectionChange`, the handlers update state, and the page renders again.
Measured at ~170 `on_nodes_change` and ~700 other frames per second on `/edge-types`,
with nodes flickering between `visibility: hidden` and visible (the root cause of the
"intermittently not visible" flakiness noted in the T-012 tests). Two fixes, both in the
wrapper:

1. `react_flow()` hoists a static `nodes`/`edges` value (a literal with no state
   dependency) into a page-level `const rrf_canvas_<n>_<prop>` emitted through
   `add_custom_code()`, and passes the constant's name as the prop. Identity is then
   stable across renders. Lists that embed a state Var are left inline, since module
   scope cannot see state.
2. `onSelectionChange` is wrapped in `rrfDedupeKeyed` (`event_utils.js`), so it reaches
   the server only when the `{node_ids, edge_ids}` payload differs from the last one
   sent for that canvas. This is REQ-010's "WHEN the selection changes" taken literally,
   and it stays a guard for state-backed canvases too.

After the fix a page load costs ~10 WebSocket frames in total, and the browser suite
passed six consecutive runs.

---

## Constitution check
- Art. 1: §1 and R-04 restate clean-room inputs; DD-002/005 designed from public docs only.
- Art. 2: DD-006 notes networkx BSD-3 — **exception requested**: extend Art. 2 wording to "MIT/Apache-2.0/BSD-permissive"; to be ratified as amendment (also flagged in PRD §8).
- Art. 4/5: DD-004/005 keep users JSX-free; §8 parity verified by prop-table tests.
- Art. 6: DD-002/003 are the required payload/debounce specs.
- Art. 7/8: §8 testing strategy binds tests to REQs; CI gate per Art. 8.

## Change History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-08 | Ernesto Crespo | Initial version |
| 1.1 | 2026-08-08 | Ernesto Crespo | DD-008: uv as package/project manager; uv.lock in structure; supply-chain note |
| 1.2 | 2026-08-08 | Ernesto Crespo | A-08 reconnect scoping in §3.3; §5.2.1 SOLID/DRY normative principles; pattern table expanded (Strategy+Registry, Command dispatch, Adapter, Factory, Template Method) |
| 1.3 | 2026-08-08 | Ernesto Crespo | T-005 spike: all §11 open questions resolved (Reflex >=0.9.8, `ReflexReactFlowWarning(UserWarning)`, no panel slot wrapper); new §12 records the five verified assumptions plus findings S-01 (Reflex camelises props natively — do not duplicate) and S-02 (npm range via the `library` string) |
| 1.4 | 2026-10-25 | Ernesto Crespo | Reflex minimum raised to 0.10.0; §12.2 re-verification (auto-memo, explicit Radix plugin, hot-reload scope) and finding S-05 (literal-prop re-render loop; static `nodes`/`edges` hoisting and selection dedupe) |
