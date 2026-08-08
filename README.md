# reflex-react-flow

Node-based editors and flow diagrams for [Reflex](https://reflex.dev), powered by
[React Flow](https://reactflow.dev) (`@xyflow/react`) v12. **Pure Python, no JavaScript.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

> **Status: pre-release (0.0.x).** Phase 0 of the implementation plan. The public API is
> specified in [`specs/`](specs/) and is being built layer by layer.

## Why

There is no community React Flow wrapper for Reflex on PyPI. The only complete wrapper
lives inside a commercially licensed product, and the official Reflex wrapping tutorial
targets the legacy `reactflow` v11 package covering roughly 10% of the API.
`reflex-react-flow` fills that gap: MIT-licensed, clean-room, and built against
`@xyflow/react` v12.

## Install

```bash
pip install reflex-react-flow
# optional LangGraph adapter
pip install "reflex-react-flow[langgraph]"
```

## Quickstart

```python
import reflex as rx
import reflex_react_flow as rxf


class State(rx.State):
    nodes: list[dict] = [
        {"id": "1", "type": "io_node", "position": {"x": 0, "y": 0},
         "data": {"label": "Start", "kind": "input"}},
        {"id": "2", "type": "card_node", "position": {"x": 250, "y": 0},
         "data": {"title": "Process", "subtitle": "does the work"}},
    ]
    edges: list[dict] = [{"id": "e1-2", "source": "1", "target": "2"}]


def index() -> rx.Component:
    return rxf.react_flow(
        rxf.background(variant="dots"),
        rxf.controls(),
        rxf.mini_map(),
        nodes=State.nodes,
        edges=State.edges,
        fit_view=True,
        height="600px",
    )
```

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
uv sync                        # create the environment
uv run pytest                  # run the test suite
uv run ruff check .            # lint
uv run pre-commit run --all-files
```

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
