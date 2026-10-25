# Analyze — reflex-react-flow · 2026-08-08

Read-only cross-artifact validation (constitution + PRD + API Spec + Tech Design +
Data Model + Plan + Tasks) against the 7-category checklist. Findings only — no
corrections applied. Approval is human.

## Findings

| # | Severity | Category | Finding | Artifacts | Suggestion |
|---|---|---|---|---|---|
| A-01 | HIGH | Constitution | Constitution Art. 2 permits only MIT/Apache-2.0 runtime deps, but the design mandates `networkx` (BSD-3-Clause). The exception is flagged in PRD §8 and Tech Design DD-006 but not ratified. | constitution, PRD, Tech Design, Plan | Amend Art. 2 to "MIT, Apache-2.0, or BSD-permissive (BSD-2/BSD-3, ISC)" via the amendments table before Phase 0 completes. |
| A-02 | HIGH | Ambiguity | `card_node.data.icon` is "icon name from bundled icon set" but no icon set is specified anywhere (which set, license, how bundled). An implementing agent would invent one — and the choice has license implications (Art. 2). | Data Model §4.1, API Spec §9 | Specify the set (e.g., a curated inline-SVG subset, MIT-licensed such as Lucide) in Data Model §4.1, including its license, before T-013. |
| A-03 | MEDIUM | Terminology | Subflow container type drifts: PRD REQ-015 says `type="group"`, Data Model §2.1 allows `"group"` or `"group_node"`, registry defines `group_node`. | PRD, Data Model, API Spec | Unify: registry `group_node` is the documented path; note React Flow's built-in `"group"` as compatible alias in one place only (Data Model). |
| A-04 | MEDIUM | Unhappy paths | Duplicate connection (user drags the same source-handle→target-handle pair twice): `FlowState.add_edge` auto-generates `e{s}-{t}-{n}` ids, so duplicates are silently added. No REQ defines whether duplicates are allowed, deduplicated, or rejected. | API Spec §6, PRD §6.3 | Add a REQ (SI...ENTONCES) defining behavior (suggest: skip + warning by default, `allow_duplicate_edges` opt-in). |
| A-05 | MEDIUM | Ambiguity | PRD states "every REQ is MUST unless marked otherwise"; REQ-018 is labeled "(optional)" — the EARS *pattern* name (WHERE) collides with priority vocabulary. REQ-035/036 marked SHOULD are unambiguous. | PRD §6 | Relabel REQ-018 as "(optional-feature pattern, priority MUST)" or move pattern names out of the priority column. |
| A-06 | MEDIUM | Executability | T-008's Done defers verification to T-012 ("via Playwright console capture in T-012") — the task cannot self-verify at completion time. | Tasks | Give T-008 a local Done (JS unit assertion via the render harness or a minimal spike page) and keep the Playwright check in T-012 as confirmation. |
| A-07 | LOW | Coverage | REQ id 019 is skipped (block boundary). Intentional per numbering blocks, but undocumented — could read as a ghost REQ. | PRD | Add a one-line note: "IDs are allocated in blocks per layer; gaps are intentional." |
| A-08 | LOW | Unhappy paths | WebSocket disconnect mid-interaction (state divergence on reconnect) is not addressed; arguably Reflex's responsibility, but the wrapper's convergence claim (Tech Design §2 "converge after every round-trip") assumes a live channel. | Tech Design | Add one line scoping reconnect behavior to Reflex; note that `nodes` prop re-push on reconnect restores canvas state. |
| A-09 | LOW | Data | INV-03 adds an edge with missing endpoints "canvas tolerates" — v12 renders nothing for dangling edges; harmless but the warning text should tell the user the edge will not render. | Data Model | Extend INV-03 warning wording. |

## Category sweep summary

1. **Coverage** — All MUST REQs (001–018, 020–025, 030–034) have ≥1 task and ≥1 planned test in the traceability matrix; SHOULDs (035/036) have Phase-4 tasks. No orphan tasks; no ghost REQs (A-07 is cosmetic). Plan phases fully covered by tasks. ✔
2. **Constitution** — One unratified exception (A-01). Naming, clean-room, event-performance, testing articles all honored in the artifacts. ✔ pending A-01
3. **Ambiguity** — Limits carry values/units (200 ms, 32 KB, ≤6 events/s, <1 s relayout, 20-node DAG). Two findings (A-02, A-05). ✔ pending fixes
4. **Terminology** — Consistent (`node.data`, registry, change deltas) except the group-type drift (A-03).
5. **Unhappy paths** — Strong: REQ-013/016/023/024/032/034/036 all SI...ENTONCES with observables. Gaps: A-04, A-08.
6. **Data** — No money/dates; ids formatted; NaN excluded; every payload schema bounded; no DB/indexes to check. ✔
7. **Task executability** — Dependency order acyclic; [P] tasks share no files; first batch T-001..T-005 identified; Done criteria are commands/observations except A-06.

## Verdict

**READY TO IMPLEMENT after resolving A-01 and A-02** (no CRITICAL findings).
Recommended order: ratify the Art. 2 amendment and pin the icon set (spec edits, ~30
min), fold A-03..A-06 into the same editing pass, then start batch T-001..T-005.

## Resolution log — 2026-08-08

All nine findings resolved in a single editing pass before Phase 0 code:

| # | Resolution | Artifact touched |
|---|---|---|
| A-01 | Art. 2 amended to "MIT, Apache-2.0, or BSD-permissive (BSD-2/BSD-3, ISC)", copyleft and source-available explicitly excluded; recorded as amendment A-2026-08-08-01 | `constitution.md` (§Art. 2, §Amendments; v1.1) |
| A-02 | Icon set pinned: curated **Lucide subset (ISC)** inlined as SVG path data in `assets/registry.jsx`, no npm dependency; 19 names listed; unknown name → no icon + console warning; notice in `assets/ICONS_LICENSE.md` | `data-model` §4.1 |
| A-03 | `group_node` declared the documented path; built-in `"group"` kept as compatible alias, stated normatively in exactly one place | `data-model` §2.1, `prd` REQ-015 |
| A-04 | New **REQ-037**: duplicate `(source, source_handle, target, target_handle)` → skip + warning; opt in with `allow_duplicate_edges` | `prd` §6.3, `api` §6/§10, `tasks` T-018 + matrix |
| A-05 | Priority vocabulary separated from EARS pattern names; REQ-018 relabelled "(optional-feature pattern, priority MUST)" | `prd` §6 preamble, REQ-018 |
| A-06 | T-008 given a local, self-verifiable Done (pytest-driven JS harness for cap + debounce); Playwright downgraded to confirmation | `tasks` T-008 |
| A-07 | ID allocation documented as per-layer blocks; gaps declared intentional | `prd` §6 preamble |
| A-08 | Reconnect behavior scoped to Reflex; prop re-push restores canvas; server state declared single source of truth | `technical` §3.3 |
| A-09 | INV-03 warning wording extended to state the edge will not render until the endpoint exists | `data-model` §5 |

**Status: cleared to implement.** Additionally, per owner instruction of 2026-08-08, the
Tech Design gained §5.2.1 (SOLID/DRY as normative engineering principles) and an expanded
pattern table (Strategy+Registry, Command dispatch, Adapter, Factory, Template Method).
