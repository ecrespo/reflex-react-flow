# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
(Constitution Art. 9).

## [Unreleased]

## [0.0.2] - 2026-10-25

First public alpha: Layer 1 (the declarative wrapper) only. The node registry,
`FlowState`, layouts and the LangGraph adapter are not in this release.

### Added
- Phase 0 scaffolding: `pyproject.toml` managed with `uv`, package skeleton under
  `custom_components/reflex_react_flow/`, MIT licensing metadata, and the governance
  test suite enforcing Constitution Art. 2 and Art. 3.
- Layer 1 wrapper: `react_flow` canvas (`rx.NoSSRComponent`, `@xyflow/react` v12 named
  imports, stylesheet injected automatically) with the full API Spec §3.1 prop table.
- Plugin components: `background`, `controls`, `mini_map`, `panel`, `node_toolbar`,
  `node_resizer`.
- Data models (`Node`, `Edge`, `EdgeMarker`, `HandleConfig`, `Viewport`) that validate on
  construction and raise `ValueError` naming the offending field.
- Fifteen event handlers whose payloads are filtered in the browser before they reach
  the WebSocket (`assets/event_utils.js`): whitelisted delta fields, a 32 KB payload cap
  (`max_event_payload_kb`) and a trailing-edge viewport debounce (`viewport_debounce_ms`).
- `flow_demo` app (quickstart, edge types, subflows, debug ledger) and a Playwright
  browser suite run in CI.
- Release workflow: a `vX.Y.Z` tag on `main` re-runs the CI gate, builds with `uv`,
  smoke-tests the wheel in a clean venv and publishes to PyPI via trusted publishing.

### Changed
- Minimum Reflex raised to **0.10.0** (`reflex>=0.10.0`); the demo pins `reflex==0.10.0`
  and declares `rx.plugins.RadixThemesPlugin()` explicitly, as Reflex 0.10 deprecates
  implicit Radix Themes enablement.
- CI actions moved to their Node 24 majors (`actions/checkout@v7`,
  `actions/setup-node@v7`, `astral-sh/setup-uv@v10.3.2`, `gitleaks/gitleaks-action@v3`,
  `actions/upload-artifact@v7`, `actions/download-artifact@v8`); Node 20 is gone from
  GitHub-hosted runners. JavaScript tests run on Node 24, and the test matrix adds
  Python 3.13.
- Constitution amended (A-2026-08-08-01): permitted runtime licenses widened to
  MIT, Apache-2.0, and BSD-permissive (BSD-2/BSD-3, ISC) so that `networkx` (BSD-3)
  and the bundled ISC icon subset are in compliance.

### Fixed
- A canvas given literal `nodes`/`edges` lists (rather than state Vars) no longer
  floods the WebSocket. The literal was rebuilt on every render, React Flow re-measured
  the "new" nodes and re-fired `on_nodes_change`/`on_selection_change`, and the state
  update that followed rendered again — ~170 events/s and flickering nodes. Static lists
  are now hoisted into page-level constants with a stable identity.
- `on_selection_change` fires only when the selection actually changes (REQ-010),
  instead of on every `nodes` prop update.

[Unreleased]: https://github.com/ecrespo/reflex-react-flow/compare/v0.0.2...HEAD
[0.0.2]: https://github.com/ecrespo/reflex-react-flow/releases/tag/v0.0.2
