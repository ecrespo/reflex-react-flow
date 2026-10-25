# Constitution — reflex-react-flow

> Version 1.1 · Ratified: 2026-08-08 · Last amended: 2026-08-08
> Scope: `github.com/ecrespo/reflex-react-flow` (PyPI package `reflex-react-flow`, import namespace `reflex_react_flow`, documented alias `import reflex_react_flow as rxf`)

This document contains the non-negotiable principles of the project. Every subsequent
artifact (PRD, API Spec, Tech Design, Data Model, Plans, Tasks) MUST include a
"Constitution check" section validating itself against these articles. An exception
without a written justification is a violation.

## Articles

### Art. 1 — Strict clean-room implementation
THE TEAM SHALL implement this package exclusively against the public API and public
documentation of `@xyflow/react` (reactflow.dev, MIT) and the public Reflex wrapping
documentation. THE TEAM SHALL NOT read, consult, or derive code from the following
prohibited sources: `reflex-enterprise` (including its "Reflex Flow" component), the
xyflow Pro examples (advanced undo/redo, copy/paste, helper lines), or any other
commercially licensed React Flow derivative. Functionality overlapping a prohibited
source SHALL be designed from scratch from public API docs only.
*Rationale: prevents license contamination and legal exposure; the project's viability
depends on a provably clean provenance chain.*

### Art. 2 — MIT license and clean dependency chain
THE PROJECT SHALL be licensed MIT (`license = "MIT"` in `pyproject.toml`, classifier
`License :: OSI Approved :: MIT License`, `LICENSE` file at repo root, © 2026 Ernesto
Crespo). THE SYSTEM SHALL NOT introduce any runtime dependency whose license is not
MIT, Apache-2.0, or BSD-permissive (BSD-2-Clause, BSD-3-Clause, ISC) — see Amendment
A-2026-08-08-01 (Reflex is Apache-2.0; `@xyflow/react` is MIT; `networkx` is BSD-3;
the bundled icon subset is ISC). Copyleft (GPL/LGPL/AGPL/MPL) and
source-available/commercial licenses SHALL NOT enter the runtime chain. The README SHALL
carry explicit attribution to xyflow/React Flow and a disclaimer of non-affiliation
with xyflow GmbH and Pynecone, Inc.
*Rationale: a single copyleft or commercial dependency would break the promise the
package makes to its downstream users.*

### Art. 3 — Naming is settled
THE TEAM SHALL use only the name `reflex-react-flow` (package, repo, docs, metadata)
and the import namespace `reflex_react_flow`. The names `reflex-flow` and
`reflex-xyflow` SHALL NOT appear in code, docs, or metadata.
*Rationale: avoids collision with the official `reflex-xy` package and the commercial
"Reflex Flow" name of Reflex Enterprise; relitigating naming wastes every discussion
it enters.*

### Art. 4 — Pythonic API first
THE SYSTEM SHALL expose a snake_case, dataclass/TypedDict-based Python API such that at
least 90% of documented use cases require zero user-written JSX. Camel-case React prop
names SHALL be translated at the wrapper boundary, never leaked to the user. The JSX
escape hatch (`node_types` with user `.jsx` assets) SHALL remain documented but
optional.
*Rationale: the package exists so Python developers never have to write JavaScript;
any API that leaks React idioms defeats its purpose.*

### Art. 5 — Declared parity with @xyflow/react v12
THE SYSTEM SHALL target `@xyflow/react` v12.x with named imports and the
`@xyflow/react/dist/style.css` stylesheet, and SHALL maintain a parity table in the
docs stating which v12 features are covered and which are explicitly out of scope with
a one-line reason each. Silent partial coverage SHALL NOT ship.
*Rationale: users must be able to tell in one glance whether their use case is
supported before adopting the package.*

### Art. 6 — Event channel performance
EVERY high-frequency event exposed by the wrapper (`on_nodes_change`,
`on_edges_change`, `on_viewport_change`, drag events) SHALL have a written event spec
defining the exact filtered payload fields that travel over the Reflex WebSocket, and
`on_viewport_change` and drag-move class events SHALL have a configurable debounce
strategy. No event SHALL serialize the full node/edge objects when a change delta
suffices.
*Rationale: unfiltered React Flow payloads saturate the Reflex WebSocket and make the
wrapper unusable beyond toy graphs.*

### Art. 7 — Mandatory testing
THE SYSTEM SHALL cover every MUST requirement (REQ-NNN) with at least one automated
test that cites its REQ ID before its task is closed: pytest for the Python layer and
integration tests against a demo Reflex app for wrapped components. No merge SHALL
land with a red test suite.
*Rationale: a wrapper's contract is behavioral; without tests, upstream Reflex or
xyflow changes break users silently.*

### Art. 8 — Quality gate and supply-chain hygiene
THE TEAM SHALL keep the pre-commit gate (Ruff, Gitleaks, pip-audit) and GitHub Actions
CI green; no merge with hooks disabled. No secret SHALL exist in code or git history.
*Rationale: the author's standard gate; catches leaks and vulnerable dependencies
before they reach PyPI.*

### Art. 9 — Semver and changelog
THE PROJECT SHALL follow Semantic Versioning; every release SHALL update
`CHANGELOG.md` (Keep a Changelog format). Breaking changes to the public Python API
SHALL only ship in a major version and SHALL be preceded by a Delta Spec in
`changes/`.
*Rationale: downstream users pin versions; unannounced breakage destroys trust in a
young package faster than any bug.*

## Stack constraints

Decided once; not re-discussed per feature:

| Area | Decision |
|---|---|
| Language | Python 3.11+ |
| Framework | Reflex (latest stable) |
| JS dependency | `@xyflow/react` v12.x (named imports, v12 CSS path) |
| JSX packaging | Local `.jsx` assets via `rx.asset` (Reflex local packages); no own JS build step |
| Layout engine | Server-side Python: `networkx` (and/or `grandalf`); zero JS layout code |
| Optional extra | `[langgraph]` for the LangGraph adapter |
| Package manager | `uv` (project + dependency management; `uv.lock` committed; CI and local workflows via `uv sync` / `uv run`) |
| Packaging | `reflex component init`, PyPI distribution (built and published with `uv build` / `uv publish`) |
| CI | GitHub Actions: Ruff, pre-commit, Gitleaks, pip-audit, pytest |
| Process | SDD spec-anchored: specs in `specs/`, changes via Delta Specs in `changes/` |

## Amendments

| Date | Article | Change | Reason | Approved by |
|---|---|---|---|---|
| 2026-08-08 (A-2026-08-08-01) | Art. 2 | Permitted runtime licenses widened from "MIT or Apache-2.0" to "MIT, Apache-2.0, or BSD-permissive (BSD-2, BSD-3, ISC)"; copyleft and source-available explicitly excluded | Resolves analyze finding A-01: the layout engine `networkx` is BSD-3-Clause and the bundled icon subset is ISC. Both are permissive and MIT-compatible; they carry no copyleft or attribution-chain obligation that would break the promise Art. 2 makes to downstream users | Ernesto Crespo |

## Constitution check (use in every artifact)

At the end of every PRD / Tech Design / Plan / Tasks document, add a 3-5 line section
stating which articles apply and how the artifact complies — or which exception is
requested and why. An exception without written justification is a violation.
