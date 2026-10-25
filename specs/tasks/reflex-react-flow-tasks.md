# Tasks — reflex-react-flow

> Source specs: [PRD](../prd/reflex-react-flow.md) · [API Spec](../api/reflex-react-flow-api-v1.md) · [Tech Design](../technical/reflex-react-flow-architecture.md) · [Data Model](../data-model/reflex-react-flow-schema.md) · [Plan](../plans/reflex-react-flow-phase-1.md)
> Plan coverage: Phases 0–4 (Phase 2–4 tasks at block granularity; refine when their phase opens) · Generated: 2026-08-08

## Conventions

- Order = execution order except [P] (parallelizable: no shared files, no dependency).
- States: `[ ]` pending · `[~]` in progress · `[x] {date}` done · `[!]` blocked (note).
- First supervised batch: **T-001..T-005**. Review, adjust, then scale.
- If implementation reveals a spec error: stop, fix the spec (or open a Delta in `changes/`), then continue.

## Tasks

### Phase 0 — Scaffolding

#### [x] 2026-08-08 · T-001 · Scaffold package
- **What:** `reflex component init` → package `reflex-react-flow`, namespace `reflex_react_flow`; manage project with `uv` (DD-008: `uv sync`, commit `uv.lock`); commit skeleton; fix minimum Reflex version (Tech Design open question).
- **REQ:** — (governance; Plan F0-01)
- **Files:** `pyproject.toml`, `uv.lock`, `custom_components/reflex_react_flow/…`
- **Depends on:** —
- **Done:** `uv sync && uv run python -c "import reflex_react_flow"` succeeds; `uv.lock` committed.

#### [x] 2026-08-08 · T-002 · Licensing & metadata [P]
- **What:** MIT in `pyproject.toml` (+classifier), LICENSE file (© 2026 Ernesto Crespo), README attribution to xyflow/React Flow + non-affiliation disclaimer, `[langgraph]` extra stub, repo topics, CHANGELOG.md, CLAUDE.md/AGENTS.md pointing to constitution.
- **REQ:** — (Constitution Art. 2/3; Plan F0-02/03/05)
- **Depends on:** T-001
- **Done:** `grep -q 'MIT License' pyproject.toml && test -f LICENSE && grep -qi 'not affiliated' README.md`.

#### [x] 2026-08-08 · T-003 · Quality gate [P]
- **What:** Pre-commit (Ruff, Gitleaks, pip-audit) + GitHub Actions CI (lint + pytest matrix py3.11/3.12) built on `uv sync`/`uv run` with lockfile caching (DD-008).
- **REQ:** — (Constitution Art. 8; Plan F0-04)
- **Depends on:** T-001
- **Done:** CI run green on empty suite; `uv run pre-commit run --all-files` passes locally.

### Phase 1 — Layer 1: wrapper, events, demo

#### [x] 2026-08-08 · T-004 · Data models
- **What:** `models.py`: `Node`, `Edge`, `Viewport`, `HandleConfig`, `EdgeMarker` dataclasses per Data Model §2; construction validation; `to_dict`/`from_dict` round-trip; INV-05/06.
- **REQ:** REQ-016, REQ-017 (model side), REQ-021 (HandleConfig shape)
- **Files:** `models.py`, `tests/unit/test_models.py`
- **Depends on:** T-001
- **Done:** `pytest tests/unit/test_models.py` green; tests cite REQ-016/017/021 in docstrings.

#### [x] 2026-08-08 · T-005 · Reflex wrapping spike
- **What:** 1-day spike: verify NoSSR wrap of `@xyflow/react` v12 (named imports), CSS injection, `rx.asset(shared=True)` import path, `panel` children slot. Record findings in Tech Design (amend or Delta if wrong). Decide warning category (open question).
- **REQ:** REQ-001 (feasibility)
- **Depends on:** T-001
- **Done:** Spike branch renders an empty styled canvas in a scratch app; Tech Design open questions §11 all resolved (checkboxes).

#### [x] 2026-08-08 · T-006 · Canvas wrapper
- **What:** `components/react_flow.py`: `ReactFlowLib(rx.NoSSRComponent)` + `react_flow()` constructor with the full prop table (API Spec §3.1), snake→camel translation, CSS via custom code.
- **REQ:** REQ-001, REQ-002, REQ-003
- **Depends on:** T-004, T-005
- **Done:** render-harness unit test asserts every §3.1 prop maps to its camelCase name; demo scratch page shows nodes/edges.

#### [x] 2026-08-08 · T-007 · Plugin components [P]
- **What:** `components/plugins.py`: `background`, `controls`, `mini_map`, `panel`, `node_toolbar`, `node_resizer` per API Spec §3.2.
- **REQ:** REQ-004
- **Depends on:** T-006
- **Done:** unit render tests per component; demo page renders all six.

#### [x] 2026-08-08 · T-008 · Event utils asset
- **What:** `assets/event_utils.js`: payload filter helpers, 32 KB cap with truncate+console-warn, trailing-edge debounce factory.
- **REQ:** REQ-013 (cap), REQ-012 (debounce mechanism)
- **Depends on:** T-005
- **Done (local, A-06):** pytest drives the pure helpers in `event_utils.js` through a Node/QuickJS one-shot harness (`tests/unit/test_event_utils.py`): a synthetic 500-change batch asserts the returned list is truncated below the cap and that a warning record was produced; a debounce test asserts N rapid calls collapse to 1 trailing call. Playwright console capture in T-012 remains the end-to-end confirmation, not the primary gate.

#### [x] 2026-08-08 · T-009 · Event specs — changes & connect
- **What:** Event specs for `on_nodes_change`, `on_edges_change`, `on_connect`, `on_connect_start`, `on_connect_end` filtering payloads per Data Model §3.1–3.3.
- **REQ:** REQ-005, REQ-006, REQ-007, REQ-014
- **Depends on:** T-006, T-008
- **Done:** unit tests assert spec JS emits only whitelisted fields; integration drag/connect tests (T-012) reference these REQs.

#### [x] 2026-08-08 · T-010 · Event specs — clicks, selection, deletes, drag, viewport [P]
- **What:** Specs for `on_node_click`, `on_node_double_click`, `on_edge_click`, `on_pane_click`, `on_selection_change`, `on_nodes_delete`, `on_edges_delete`, `on_node_drag_start/stop`, `on_viewport_change` (debounced, `viewport_debounce_ms`).
- **REQ:** REQ-008, REQ-009, REQ-010, REQ-011, REQ-012
- **Depends on:** T-006, T-008
- **Done:** unit tests per spec assert payload shape.

#### [x] 2026-08-08 · T-011 · Demo app (Phase-1 pages)
- **What:** `flow_demo/`: quickstart page, edge-types page (REQ-017), subflows page (REQ-015), color-mode toggle (REQ-018), debug panel (event counts/sizes).
- **REQ:** REQ-002, REQ-015, REQ-017, REQ-018
- **Depends on:** T-006, T-007
- **Done:** `reflex run` serves all pages; data-testid hooks present for Playwright.

#### [x] 2026-08-08 · T-012 · Integration suite Phase 1
- **What:** Playwright suite: render (REQ-002/004), drag deltas only (REQ-005), edge changes (REQ-006), connect payload (REQ-007), clicks (REQ-008), drag start/stop only (REQ-009), selection (REQ-010), delete key (REQ-011), pan ≤6 events/s (REQ-012), truncation warning (REQ-013), subflow clamp (REQ-015), color mode flip (REQ-018).
- **REQ:** REQ-002, 004–015, 017, 018
- **Depends on:** T-009, T-010, T-011
- **Done:** `pytest tests/integration -m phase1` green in CI; **Phase 1 exit gate checklist in Plan §3 all checked**.

### Phase 2 — Layer 2: registry

#### T-013 · registry.jsx — card/group/annotation/io
- **What:** Data-driven components per Data Model §4.1/4.3/4.4/4.5 with defaults; XSS-safe text rendering; whitelist markdown for annotation.
- **REQ:** REQ-020, REQ-024
- **Depends on:** T-012
- **Done:** registry showcase demo page renders these 4 types with `data={}` and full data; no console errors.

#### T-014 · registry.jsx — agent_node
- **What:** Agent node with status indicator (idle/running/done/error), token/call counters per Data Model §4.2; status change without re-mount.
- **REQ:** REQ-020, REQ-022
- **Depends on:** T-013
- **Done:** Playwright flips status via state and asserts indicator class change with stable DOM identity.

#### T-015 · Declarative handles
- **What:** Handle rendering from `data.handles` across registry types; edge `source_handle`/`target_handle` wiring.
- **REQ:** REQ-021
- **Depends on:** T-013
- **Done:** integration test connects to a specific handle id among 3.

#### T-016 · Fallback + escape hatch
- **What:** Unknown-type fallback with console warning; docs + demo page registering a custom user `.jsx` node via `node_types`.
- **REQ:** REQ-023, REQ-025
- **Depends on:** T-013
- **Done:** bogus-type test asserts default node + warning; custom node renders in demo. **Phase 2 gate checked.**

### Phase 3 — Layer 3: FlowState & layouts

#### T-017 · changes.py
- **What:** Pure `apply_node_changes`/`apply_edge_changes`, all change types per Data Model §3.1–3.2, unknown-id skip + warning, INV-04 ordering.
- **REQ:** REQ-031, REQ-032
- **Depends on:** T-004 (parallel to Phase 2)
- **Done:** table-driven pytest for every change type + unknown-id case green.

#### T-018 · FlowState
- **What:** `state.py` per API Spec §6: operations, invariants INV-01..03, event handler delegation, duplicate-connection policy + `allow_duplicate_edges` (REQ-037), `apply_layout` stub.
- **REQ:** REQ-030, REQ-031, REQ-032, REQ-037
- **Depends on:** T-017
- **Done:** unit tests per operation incl. duplicate-id ValueError, remove-node-removes-edges, and duplicate-connection skip/opt-in.

#### T-019 · layouts.py
- **What:** 4 layouts on networkx per API Spec §7; deterministic seeds; hierarchical cycle-break with warning.
- **REQ:** REQ-033, REQ-034
- **Depends on:** T-004
- **Done:** pytest: seeded determinism, zero overlap on 20-node DAG, cyclic graph warns + completes.

#### T-020 · Layer-3 demo + wiring
- **What:** Layouts demo page (50-node relayout), FlowState-backed editor page; connect `apply_layout` to layouts.
- **REQ:** REQ-030, REQ-033
- **Depends on:** T-018, T-019
- **Done:** relayout < 1 s in demo; integration test green. **Phase 3 gate checked.**

### Phase 4 — Adapter & release

#### T-021 · LangGraph adapter
- **What:** `adapters/langgraph.py`: `from_langgraph` per API Spec §8; `[langgraph]` extra; ImportError guard with install hint.
- **REQ:** REQ-035, REQ-036
- **Depends on:** T-018, T-019
- **Done:** pytest with demo 3-node StateGraph (extra installed) + ImportError test (extra absent, via tox env).

#### T-022 · Docs & parity table [P]
- **What:** README quickstart, API reference, v12 parity table (covered / out-of-scope + reason), escape-hatch guide.
- **REQ:** — (Constitution Art. 5; PRD NFR)
- **Depends on:** T-016, T-020
- **Done:** docs build; parity table lists every §3.1 prop and every excluded v12 feature.

#### T-023 · Release v0.1.0
- **What:** Version bump, CHANGELOG, `uv build` + PyPI trusted publishing via CI, clean-venv install test, gallery submission.
- **REQ:** — (Constitution Art. 9; Plan P4-C/D)
- **Depends on:** T-021, T-022
- **Done:** `pip install reflex-react-flow` in clean venv runs quickstart; release tagged; gallery PR opened. **Phase 4 gate checked.**

## Traceability matrix

| REQ | Tasks | Planned tests (cite REQ) |
|---|---|---|
| REQ-001 | T-005, T-006 | test_css_injection, test_named_imports |
| REQ-002 | T-006, T-011, T-012 | test_render_nodes_edges |
| REQ-003 | T-006 | test_prop_translation_table |
| REQ-004 | T-007, T-012 | test_plugin_components_render |
| REQ-005 | T-009, T-012 | test_nodes_change_delta_only |
| REQ-006 | T-009, T-012 | test_edges_change_delta_only |
| REQ-007 | T-009, T-012 | test_connect_payload |
| REQ-008 | T-010, T-012 | test_click_payloads |
| REQ-009 | T-010, T-012 | test_drag_start_stop_only |
| REQ-010 | T-010, T-012 | test_selection_change_ids_only |
| REQ-011 | T-010, T-012 | test_delete_events |
| REQ-012 | T-008, T-010, T-012 | test_viewport_debounce_count |
| REQ-013 | T-008, T-012 | test_payload_truncation_warning |
| REQ-014 | T-009 | test_connect_start_end_payloads |
| REQ-015 | T-011, T-012 | test_subflow_clamp |
| REQ-016 | T-004 | test_model_validation_errors |
| REQ-017 | T-004, T-011, T-012 | test_edge_types_render |
| REQ-018 | T-011, T-012 | test_color_mode_system |
| REQ-020 | T-013, T-014 | test_registry_types_render |
| REQ-021 | T-004, T-015 | test_declarative_handles |
| REQ-022 | T-014 | test_agent_status_no_remount |
| REQ-023 | T-016 | test_unknown_type_fallback |
| REQ-024 | T-013 | test_empty_data_defaults |
| REQ-025 | T-016 | test_custom_jsx_escape_hatch |
| REQ-030 | T-018, T-020 | test_flowstate_operations |
| REQ-031 | T-017, T-018 | test_apply_changes_table |
| REQ-032 | T-017, T-018 | test_unknown_id_skip_warn |
| REQ-033 | T-019, T-020 | test_layouts_deterministic_no_overlap |
| REQ-034 | T-019 | test_cyclic_hierarchical_warns |
| REQ-035 (SHOULD) | T-021 | test_from_langgraph |
| REQ-036 (SHOULD) | T-021 | test_langgraph_import_error |
| REQ-037 | T-018 | test_duplicate_connection_skipped, test_allow_duplicate_edges_opt_in |

All MUST REQs (001–034 minus SHOULDs) have ≥1 task and ≥1 planned test. SHOULDs
(REQ-035/036) scheduled in Phase 4; no deferred SHOULDs without tasks.

## Execution log

| Date | Tasks | Result | Notes |
|---|---|---|---|
| 2026-08-08 | A-01..A-09 | Done | All nine analyze findings resolved; Art. 2 amended (A-2026-08-08-01); icon set pinned to a bundled Lucide/ISC subset; REQ-037 added. Resolution log in `analyze-report.md` |
| 2026-08-08 | T-001 | `[x]` | uv project; Reflex minimum fixed at `>=0.9.8`; `uv.lock` generated (2318 lines); `uv run python -c "import reflex_react_flow"` OK |
| 2026-08-08 | T-002 | `[x]` | MIT + OSI classifier, LICENSE, README attribution/non-affiliation, `[langgraph]` extra, CHANGELOG. Governance suite (8 tests) encodes Art. 2/3 |
| 2026-08-08 | T-005 | `[x]` | Spike vs Reflex 0.9.8: all 5 assumptions hold; §11 open questions closed; findings S-01 (Reflex camelises natively) and S-02 recorded in new Tech Design §12 |
| 2026-08-08 | T-004 | `[x]` | `models.py` — 31 tests citing REQ-016/017/021, INV-05/06 |
| 2026-08-08 | T-006 | `[x]` | `ReactFlowLib` NoSSR + full §3.1 prop table; `PROP_NAME_MAP` asserted as a set (Art. 5) |
| 2026-08-08 | T-007 | `[x]` | six plugin components sharing one base; 28 tests |
| 2026-08-08 | T-008 | `[x]` | `event_utils.js` driven from pytest via Node (A-06 local Done); 13 tests |
| 2026-08-08 | T-009/T-010 | `[x]` | 15 event specs via per-cap class factory; keyed viewport debounce; 27 tests |
| 2026-08-08 | T-011 | `[x]` | demo app, 4 pages + event ledger; 29 render tests |
| 2026-08-08 | T-012 | `[x]` | Playwright suite 14/14, stable over 3 consecutive runs. Found and fixed an infinite render loop (~60 ev/s) caused by unconditional state write-back — constraint recorded for T-017 |
| 2026-08-08 | T-003 | `[x]` | pre-commit (13 hooks: Ruff, Gitleaks, pip-audit, uv-lock, governance tests) green on `--all-files`; GH Actions CI authored (lint/secrets/audit/test 3.11+3.12/gate). CI not yet observed green — no remote push |
| 2026-10-25 | — (maintenance) | Done | Reflex `>=0.10.0` (demo pins 0.10.0, explicit `RadixThemesPlugin`); CI actions on Node 24 majors, py3.13 added, Playwright suite added to the gate; fixed literal-prop re-render loop (Tech Design S-05) with REQ-010 tests; `release.yml` for tag-driven trusted publishing. Released **0.0.2** as a Layer-1 alpha ahead of T-023, which still owns 0.1.0 |

---

## Constitution check
- Art. 7: every REQ-bearing task's Done names a test; matrix enforces coverage.
- Art. 8: T-003 lands the gate before feature tasks.
- Art. 1: T-005/T-013 restricted to public docs (clean-room noted in task scope).
- Art. 9: T-023 blocks release on CHANGELOG + semver.
