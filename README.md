# reflex-react-flow

Node-based editors and flow diagrams for [Reflex](https://reflex.dev), powered by
[React Flow](https://reactflow.dev) (`@xyflow/react`) v12. **Pure Python, no JavaScript.**

[![PyPI](https://img.shields.io/pypi/v/reflex-react-flow.svg)](https://pypi.org/project/reflex-react-flow/)
[![CI](https://github.com/ecrespo/reflex-react-flow/actions/workflows/ci.yml/badge.svg)](https://github.com/ecrespo/reflex-react-flow/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Reflex 0.10+](https://img.shields.io/badge/reflex-0.10%2B-5646ED.svg)](https://reflex.dev)

> **Status: alpha (0.0.2).** Layer 1 of the implementation plan — the declarative
> canvas wrapper, plugins, data models and filtered event channel — is complete. The
> public API is specified in [`specs/`](specs/) and the remaining layers are in progress;
> see [What's in this release](#whats-in-this-release).

## Why

There is no community React Flow wrapper for Reflex on PyPI. The only complete wrapper
lives inside a commercially licensed product, and the official Reflex wrapping tutorial
targets the legacy `reactflow` v11 package covering roughly 10% of the API.
`reflex-react-flow` fills that gap: MIT-licensed, clean-room, and built against
`@xyflow/react` v12.

## Install

Requires **Python 3.11+** and **Reflex 0.10.0 or newer**.

```bash
pip install reflex-react-flow
# or, in a uv-managed project
uv add reflex-react-flow
```

The `@xyflow/react` v12 npm package is installed by Reflex automatically the first time
the app compiles — there is nothing to add to `package.json`.

## Quickstart

```python
import reflex as rx
import reflex_react_flow as rxf


class State(rx.State):
    nodes: list[dict] = [
        {"id": "1", "type": "input", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}},
        {"id": "2", "position": {"x": 250, "y": 0}, "data": {"label": "Process"}},
    ]
    edges: list[dict] = [{"id": "e1-2", "source": "1", "target": "2", "animated": True}]

    @rx.event
    def on_node_click(self, node: dict) -> None:
        print("clicked", node["id"])  # payload is filtered to {id, type, position}


def index() -> rx.Component:
    # React Flow sizes itself to its *parent*: give the wrapper the dimensions,
    # not the canvas (a `height=` on the canvas itself collapses it).
    return rx.box(
        rxf.react_flow(
            rxf.background(variant="dots"),
            rxf.controls(),
            rxf.mini_map(),
            nodes=State.nodes,
            edges=State.edges,
            on_node_click=State.on_node_click,
            fit_view=True,
        ),
        width="100%",
        height="600px",
    )


app = rx.App()
app.add_page(index)
```

`nodes` and `edges` may also be plain Python lists for a static diagram; the wrapper
hoists them into page-level constants so React Flow sees a stable array.

## What's in this release

| Area | 0.0.2 | Notes |
|---|---|---|
| Canvas `react_flow` + API Spec §3.1 props | ✅ | snake_case props, v12 stylesheet injected |
| Plugins: `background`, `controls`, `mini_map`, `panel`, `node_toolbar`, `node_resizer` | ✅ | |
| Models: `Node`, `Edge`, `EdgeMarker`, `HandleConfig`, `Viewport` | ✅ | validate on construction |
| 15 event handlers, filtered in the browser | ✅ | 32 KB cap, 200 ms viewport debounce |
| Built-in node types (`default`, `input`, `output`, `group`) | ✅ | React Flow's own |
| Generic node registry (`card_node`, `agent_node`, …) | ⏳ | Phase 2 |
| `FlowState`, `apply_node_changes`, layouts | ⏳ | Phase 3 |
| `from_langgraph` adapter / `[langgraph]` extra | ⏳ | Phase 4 — the extra installs LangGraph but the adapter is not shipped yet |

The full v12 parity table (covered vs. out-of-scope, with reasons) lands with the 0.1.0
release (Constitution Art. 5).

## Documentation

| Document | Contents |
|---|---|
| [Constitution](specs/constitution.md) | Non-negotiable project principles |
| [PRD](specs/prd/reflex-react-flow.md) | Requirements (EARS, `REQ-NNN`) |
| [API Spec v1](specs/api/reflex-react-flow-api-v1.md) | Public Python surface |
| [Tech Design](specs/technical/reflex-react-flow-architecture.md) | Architecture and design decisions |
| [Data Model](specs/data-model/reflex-react-flow-schema.md) | `Node`/`Edge`/`node.data` schemas |

## Development

This project is managed with [uv](https://docs.astral.sh/uv/):

```bash
uv sync --all-extras           # create the environment
uv run pytest tests/unit       # unit suite (the event_utils.js tests need Node 24)
uv run ruff check .            # lint
uv run pre-commit run --all-files
```

The browser suite drives the demo app with Playwright:

```bash
uv run playwright install chromium
cd flow_demo && uv run --project .. reflex run   # terminal 1
uv run pytest tests/integration                  # terminal 2, from the repo root
```

Reflex's hot reload watches the demo app only — restart `reflex run` after editing
anything under `custom_components/`.

### Releasing

Releases are cut from `main` by a semver tag; [`release.yml`](.github/workflows/release.yml)
does the rest.

1. Bump `version` in `pyproject.toml` and `__version__` in
   `custom_components/reflex_react_flow/__init__.py` (a test keeps them equal), and move
   the `[Unreleased]` notes in `CHANGELOG.md` under the new version.
2. Merge `develop` into `main` through a PR with a green CI gate.
3. Tag the merge commit and push the tag:
   ```bash
   git switch main && git pull
   git tag -a v0.0.2 -m "v0.0.2" && git push origin v0.0.2
   ```
4. The workflow checks that the tag matches `pyproject.toml`, sits on `main` and has a
   CHANGELOG entry; re-runs the full CI gate; builds with `uv build`; installs the wheel
   in a clean venv; publishes to PyPI through **trusted publishing** (no token in the
   repo); and creates the GitHub release.

One-time PyPI setup: register a trusted publisher for project `reflex-react-flow` with
owner `ecrespo`, repository `reflex-react-flow`, workflow `release.yml` and environment
`pypi`.

## License and attribution

`reflex-react-flow` is released under the [MIT License](LICENSE), © 2026 Ernesto Crespo.

This package wraps **[React Flow](https://reactflow.dev)** (`@xyflow/react`), an MIT-licensed
library by **xyflow GmbH** — all credit for the underlying canvas engine belongs to them.
Node icons are a curated subset of [Lucide](https://lucide.dev) (ISC License).

**Disclaimer of non-affiliation.** This is an independent, community-maintained project.
It is **not affiliated with, endorsed by, or sponsored by xyflow GmbH** (the authors of
React Flow) **or Pynecone, Inc.** (the authors of Reflex). "React Flow" and "Reflex" are
the property of their respective owners.

This package is a **clean-room implementation** built exclusively against the public
documentation of `@xyflow/react` and the public Reflex component-wrapping documentation
(Constitution Art. 1).
