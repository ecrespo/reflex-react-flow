# reflex-react-flow — Implementation Plan (Phases 0–4)

## Metadata

| Field | Value |
|---|---|
| **Author** | Ernesto Crespo |
| **Status** | `DRAFT` |
| **Version** | 1.0 |
| **Date** | 2026-08-08 |
| **PRD** | [specs/prd/reflex-react-flow.md](../prd/reflex-react-flow.md) |
| **Tech Design** | [specs/technical/reflex-react-flow-architecture.md](../technical/reflex-react-flow-architecture.md) |
| **Data Model** | [specs/data-model/reflex-react-flow-schema.md](../data-model/reflex-react-flow-schema.md) |
| **API Spec** | [specs/api/reflex-react-flow-api-v1.md](../api/reflex-react-flow-api-v1.md) |

---

## 1. Implementation Summary

Five phases aligned to the three architecture layers plus scaffolding and release.
Solo maintainer, part-time cadence; estimates are working days (d), not calendar
days. Each phase ends with a verifiable exit gate; Tasks are generated per phase
(this repo's `specs/tasks/` covers Phases 0–1 initially; later phases get their task
files when their predecessor gate passes).

**Total estimate:** ~30–38 working days across 5 phases.
**Team:** 1 developer (Ernesto Crespo).
**Production target:** v0.1.0 on PyPI at Phase 4 gate.

## 2. Prerequisites

| Prerequisite | Owner | Status | Deadline |
|---|---|---|---|
| Specs approved (this kit, post-Analyze) | EC | ☐ | before Phase 1 |
| Constitution amendment ratified (BSD-permissive deps — networkx) | EC | ☐ | with spec approval |
| GitHub repo topics + branch protection configured | EC | ☐ | Phase 0 |
| Minimum Reflex version fixed (Tech Design open question) | EC | ☐ | Phase 0 |

## 3. Phases

---

### Phase 0: Scaffolding & Governance

**Duration:** 2–3 d
**Goal:** Package skeleton, quality gate, and legal baseline in place.

| ID | Task | Est. | Deps | Status |
|---|---|---|---|---|
| F0-01 | `reflex component init` with package name `reflex-react-flow`; namespace `reflex_react_flow` | 0.5d | — | ☐ |
| F0-02 | `pyproject.toml` managed with `uv` (Tech Design DD-008): MIT license + classifier, Python ≥3.11, `[langgraph]` extra stub, pins; commit `uv.lock` | 0.5d | F0-01 | ☐ |
| F0-03 | LICENSE (MIT © 2026 Ernesto Crespo); README with xyflow attribution + non-affiliation disclaimer | 0.5d | F0-01 | ☐ |
| F0-04 | Pre-commit gate: Ruff, Gitleaks, pip-audit; GitHub Actions CI (lint + test matrix) running on `uv sync` / `uv run` with lockfile caching | 1d | F0-01 | ☐ |
| F0-05 | Repo hygiene: topics (reflex, react-flow, xyflow, python, node-editor, flow-chart, graph-visualization, diagrams, langgraph, custom-component), CHANGELOG.md, CLAUDE.md/AGENTS.md → constitution | 0.5d | F0-03 | ☐ |

**Exit gate (verifiable):**
- `uv sync && uv run python -c "import reflex_react_flow"` succeeds; `uv.lock` committed.
- CI green on an empty test suite (uv-based); pre-commit hooks run on commit.
- `pyproject.toml` shows MIT license/classifier; README contains attribution text.

---

### Phase 1: Layer 1 — Wrapper, events, demo app

**Duration:** 10–12 d
**Goal:** Full declarative wrapper of the v12 prop-driven API with filtered events, proven by a demo app and integration tests.
**Covers:** REQ-001–018 (+ REQ-016 validation in models).

Work breakdown (detail in `specs/tasks/reflex-react-flow-tasks.md`):

| Block | Content | Est. |
|---|---|---|
| P1-A Models | `Node`, `Edge`, `Viewport`, `HandleConfig`, `EdgeMarker` + validation + round-trip | 2d |
| P1-B Canvas wrapper | `ReactFlowLib` NoSSR component, prop table, CSS injection | 2d |
| P1-C Plugin components | background/controls/mini_map/panel/node_toolbar/node_resizer | 1.5d |
| P1-D Event specs | event_utils.js + 15 event specs with filtering/debounce/cap | 3d |
| P1-E Demo app | quickstart page, edge-types page, subflows page, debug panel | 2d |
| P1-F Integration tests | Playwright suite for REQ-002..018 | 2d |

**Exit gate (verifiable):**
- Demo app: styled canvas, all plugin components, one edge of each type, a subflow — rendered from Python only.
- Playwright suite green; drag test observes only filtered payloads (REQ-005/009).
- Pan-for-1s test produces ≤ 6 viewport events (REQ-012); 500-change synthetic batch truncates + warns (REQ-013).
- Unit tests cite every REQ-001..018 at least once (`grep -r "REQ-0" tests/` maps 100%).

---

### Phase 2: Layer 2 — Generic node registry

**Duration:** 6–8 d
**Goal:** The 5 data-driven node types shipping as a local `.jsx` asset; declarative handles; escape hatch documented.
**Covers:** REQ-020–025.

| Block | Content | Est. |
|---|---|---|
| P2-A registry.jsx | 5 components, data-driven, defaults per Data Model §4 | 3d |
| P2-B Handles | `data.handles` rendering + edge-to-handle wiring | 1d |
| P2-C Fallback & robustness | unknown type fallback, `data={}` renders, status transitions without re-mount | 1d |
| P2-D Escape hatch | docs + demo custom user node via `node_types` | 1d |
| P2-E Tests | integration suite REQ-020..025; registry showcase demo page | 1.5d |

**Exit gate (verifiable):**
- Registry showcase page renders all 5 types from Python dicts with `data={}` and with full data.
- Connect-to-specific-handle test passes (REQ-021); agent status flip keeps DOM identity (REQ-022).
- Bogus type renders default node + console warning captured by Playwright (REQ-023).
- Custom user JSX node renders in demo (REQ-025).

---

### Phase 3: Layer 3 — FlowState & layouts

**Duration:** 6–7 d
**Goal:** High-level Python API: state container, change application, server-side layouts.
**Covers:** REQ-030–034.

| Block | Content | Est. |
|---|---|---|
| P3-A changes.py | `apply_node_changes`/`apply_edge_changes`, all change types, pure | 2d |
| P3-B FlowState | operations, invariants INV-01..06, event handler wiring | 2d |
| P3-C layouts.py | 4 algorithms on networkx; determinism; cycle-break | 2d |
| P3-D Demo + tests | layouts demo page; unit suites REQ-030..034 | 1d |

**Exit gate (verifiable):**
- Table-driven change tests green for every change type (REQ-031); unknown-id changes warn and no-op (REQ-032).
- 20-node DAG: hierarchical layout deterministic (seeded) with zero node overlaps (REQ-033); cyclic graph lays out with warning (REQ-034).
- Demo "layout" page relayouts a 50-node graph server-side in < 1 s.

---

### Phase 4: Adapter, release & ecosystem

**Duration:** 5–6 d
**Goal:** LangGraph adapter, docs, v0.1.0 on PyPI, gallery submission.
**Covers:** REQ-035–036 + release NFRs.

| Block | Content | Est. |
|---|---|---|
| P4-A Adapter | `from_langgraph` + `[langgraph]` extra + ImportError guard | 1.5d |
| P4-B Docs | README quickstart, API reference, v12 parity table, escape-hatch guide | 2d |
| P4-C Release | version 0.1.0, CHANGELOG, `uv build` + PyPI publish via CI (trusted publishing) | 1d |
| P4-D Ecosystem | Reflex component gallery submission; announce | 0.5d |

**Decision point (from PRD §5.3 / DD-007):** adapter ships in-package as extra for
v0.1.0. Split into `reflex-langgraph-flow` only if post-launch demand justifies it —
via Delta Spec.

**Exit gate (verifiable):**
- `pip install reflex-react-flow[langgraph]`; demo StateGraph renders as agent graph (REQ-035); missing-extra ImportError message test (REQ-036).
- `pip install reflex-react-flow` from PyPI works in a clean venv; quickstart runs.
- Docs published with parity table; gallery PR submitted.
- Full test suite green; traceability matrix in tasks file shows 100% MUST coverage.

---

## 4. Dependency map

```
Phase 0 ──▶ Phase 1 (Layer 1) ──▶ Phase 2 (Layer 2) ──▶ Phase 4 (release)
                    │                                        ▲
                    └──────────▶ Phase 3 (Layer 3) ──────────┘
```

Phase 3 depends only on Phase 1 (models + events); it can start before Phase 2
finishes if needed — Phases 2 and 3 are parallelizable for a second contributor.

## 5. Implementation risks

| Risk | Prob. | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Reflex wrapping quirks (slots, asset paths) burn Phase 1 time | Med | High | 1-day spike at P1 start (panel children, asset import) before committing to estimates | EC |
| Playwright flakiness on canvas interactions | Med | Med | data-testid hooks in demo; retry policy; deterministic seeds | EC |
| Solo-maintainer stalls | Med | Med | Phase gates small and independently shippable; pre-releases from Phase 1 | EC |
| Scope creep toward Pro features | Low | High | Constitution Art. 1 + PRD §5.2 as the gate | EC |

## 6. Tracking

Progress is tracked in `specs/tasks/reflex-react-flow-tasks.md` (checkboxes + dates)
so any session — human or agent — can resume. Weekly self-review: tasks done /
planned / blocked; deviations from spec open a Delta in `changes/`.

## 7. Global Definition of Done

- [ ] Code merged to `main` with CI green (Ruff, Gitleaks, pip-audit, pytest, Playwright)
- [ ] Every touched MUST REQ has a test citing it
- [ ] Docs updated (README/API/parity table)
- [ ] CHANGELOG entry; semver respected
- [ ] Spec updated (or Delta opened) if implementation deviated

---

## Constitution check
- Art. 1/2/3: F0-02/F0-03/F0-05 implement licensing, attribution, naming; clean-room guarded via risk table.
- Art. 6: Phase 1 gate measures debounce/cap behavior directly.
- Art. 7: every phase gate requires REQ-cited tests; traceability matrix at Phase 4.
- Art. 8: F0-04 sets the gate before any feature code exists.
- Art. 9: Phase 4 release blocks on CHANGELOG + semver.

## Change History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-08 | Ernesto Crespo | Initial version |
| 1.1 | 2026-08-08 | Ernesto Crespo | Phase 0 and release blocks updated to uv workflow (DD-008) |
