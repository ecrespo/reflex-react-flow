# reflex-react-flow — Public Python API Specification (v1)

## Metadata

| Field | Value |
|---|---|
| **Author** | Ernesto Crespo |
| **Status** | `DRAFT` |
| **API Version** | v1.0 |
| **Date** | 2026-08-08 |
| **Related PRD** | [specs/prd/reflex-react-flow.md](../prd/reflex-react-flow.md) |
| **Import namespace** | `reflex_react_flow` (documented alias `import reflex_react_flow as rxf`) |

The "API" of this package is its public Python surface: component constructors,
data models, `FlowState`, the layout module, and the registry `node.data` contract.
Anything not listed here is private (`_`-prefixed) and may change without semver
guarantees. Breaking changes to this document require a major version and a Delta
Spec (Constitution Art. 9).

---

## 1. Overview

```python
import reflex as rx
import reflex_react_flow as rxf

def index():
    return rxf.react_flow(
        rxf.background(variant="dots"),
        rxf.controls(),
        rxf.mini_map(),
        nodes=FlowDemo.nodes,
        edges=FlowDemo.edges,
        on_connect=FlowDemo.on_connect,
        color_mode="system",
        fit_view=True,
    )
```

Top-level exports (`reflex_react_flow.__all__`):

| Export | Kind | Layer |
|---|---|---|
| `react_flow` | component constructor | 1 |
| `background`, `controls`, `mini_map`, `panel`, `node_toolbar`, `node_resizer` | component constructors | 1 |
| `Node`, `Edge`, `Viewport`, `HandleConfig`, `EdgeMarker` | data models | 1 |
| `NodeChange`, `EdgeChange`, `Connection` | event payload models | 1 |
| `FlowState` | state base class | 3 |
| `layouts` (module: `layout_hierarchical`, `layout_force`, `layout_circular`, `layout_layered`) | functions | 3 |
| `from_langgraph` | adapter (extra `[langgraph]`) | 3 |
| `apply_node_changes`, `apply_edge_changes` | pure helpers | 3 |
| `CARD_NODE`, `AGENT_NODE`, `GROUP_NODE`, `ANNOTATION_NODE`, `IO_NODE` | node-type string constants | 2 |

## 2. Conventions

- All Python props snake_case; translated to camelCase at the wrapper boundary (REQ-003). React prop names never leak.
- All models serialize to plain JSON-compatible dicts (see Data Model spec for schemas).
- Validation errors at construction time raise `ValueError` naming the field (REQ-016).
- Event handlers are optional `rx.EventHandler` props with typed, filtered event specs (REQ-005–014).

## 3. Components (Layer 1)

### 3.1 `react_flow(*children, **props) -> rx.Component`

**Description:** Main canvas. Children: plugin components and `panel` content.

**Props:**

| Python prop | Type | Default | React prop | REQ |
|---|---|---|---|---|
| `nodes` | `list[Node] \| rx.Var` | `[]` | `nodes` | REQ-002 |
| `edges` | `list[Edge] \| rx.Var` | `[]` | `edges` | REQ-002 |
| `node_types` | `dict[str, rx.Var]` | registry defaults | `nodeTypes` | REQ-020/025 |
| `edge_types` | `dict[str, rx.Var]` | `{}` | `edgeTypes` | REQ-003 |
| `color_mode` | `Literal["light","dark","system"]` | `"system"` | `colorMode` | REQ-018 |
| `fit_view` | `bool` | `False` | `fitView` | REQ-003 |
| `default_edge_options` | `dict` | `None` | `defaultEdgeOptions` | REQ-003 |
| `connection_mode` | `Literal["strict","loose"]` | `"strict"` | `connectionMode` | REQ-003 |
| `snap_to_grid` | `bool` | `False` | `snapToGrid` | REQ-003 |
| `snap_grid` | `tuple[int, int]` | `(15, 15)` | `snapGrid` | REQ-003 |
| `min_zoom` | `float` | `0.5` | `minZoom` | REQ-003 |
| `max_zoom` | `float` | `2.0` | `maxZoom` | REQ-003 |
| `translate_extent` | `list[list[float]]` | infinite | `translateExtent` | REQ-003 |
| `node_extent` | `list[list[float]]` | infinite | `nodeExtent` | REQ-003 |
| `nodes_draggable` | `bool` | `True` | `nodesDraggable` | REQ-003 |
| `nodes_connectable` | `bool` | `True` | `nodesConnectable` | REQ-003 |
| `nodes_focusable` | `bool` | `True` | `nodesFocusable` | REQ-003 |
| `edges_focusable` | `bool` | `True` | `edgesFocusable` | REQ-003 |
| `elements_selectable` | `bool` | `True` | `elementsSelectable` | REQ-003 |
| `pan_on_drag` | `bool` | `True` | `panOnDrag` | REQ-003 |
| `zoom_on_scroll` | `bool` | `True` | `zoomOnScroll` | REQ-003 |
| `delete_key_code` | `str \| list[str] \| None` | `"Backspace"` | `deleteKeyCode` | REQ-011 |
| `viewport` | `Viewport` | `None` (uncontrolled) | `viewport` | REQ-003 |
| `default_viewport` | `Viewport` | `{x:0,y:0,zoom:1}` | `defaultViewport` | REQ-003 |
| `viewport_debounce_ms` | `int` | `200` | (wrapper-level) | REQ-012 |
| `max_event_payload_kb` | `int` | `32` | (wrapper-level) | REQ-013 |

**Event handler props** (payload models in §5; all optional):

| Prop | Payload (spec-filtered) | REQ |
|---|---|---|
| `on_nodes_change` | `list[NodeChange]` | REQ-005 |
| `on_edges_change` | `list[EdgeChange]` | REQ-006 |
| `on_connect` | `Connection` | REQ-007 |
| `on_connect_start` | `{node_id, handle_id, handle_type}` | REQ-014 |
| `on_connect_end` | `{connected: bool}` | REQ-014 |
| `on_node_click` / `on_node_double_click` | `{id, type, position}` | REQ-008 |
| `on_node_drag_start` / `on_node_drag_stop` | `{id, position}` | REQ-009 |
| `on_edge_click` | `{id, type}` | REQ-008 |
| `on_pane_click` | `{position}` (flow coords) | REQ-008 |
| `on_selection_change` | `{node_ids, edge_ids}` | REQ-010 |
| `on_nodes_delete` / `on_edges_delete` | `list[str]` (ids) | REQ-011 |
| `on_viewport_change` | `Viewport` (debounced) | REQ-012 |

### 3.2 Plugin components

| Constructor | Key props (snake_case) | React component | REQ |
|---|---|---|---|
| `background(variant="dots"\|"lines"\|"cross", gap=20, size=1, color=None)` | variant, gap, size, color | `Background` | REQ-004 |
| `controls(show_zoom=True, show_fit_view=True, show_interactive=True, position="bottom-left")` | — | `Controls` | REQ-004 |
| `mini_map(pannable=False, zoomable=False, node_color=None, position="bottom-right")` | — | `MiniMap` | REQ-004 |
| `panel(*children, position="top-left")` | position | `Panel` | REQ-004 |
| `node_toolbar(*children, is_visible=None, position="top", offset=10)` | — | `NodeToolbar` | REQ-004 |
| `node_resizer(min_width=10, min_height=10, is_visible=True, color=None)` | — | `NodeResizer` | REQ-004 |

Positions use the v12 panel position enum:
`"top-left" | "top-center" | "top-right" | "bottom-left" | "bottom-center" | "bottom-right"`.

## 4. Data models (Layer 1)

Full field-by-field schemas (types, required, defaults, validation) live in the
[Data Model spec](../data-model/reflex-react-flow-schema.md). Summary of constructors:

```python
Node(
    id: str,                        # required
    position: tuple[float, float] | dict,  # required → {x, y}
    data: dict = {},
    type: str = "default",          # registry constant or custom
    parent_id: str | None = None,   # subflows (REQ-015)
    extent: Literal["parent"] | list | None = None,
    width: float | None = None,
    height: float | None = None,
    draggable: bool | None = None,
    selectable: bool | None = None,
    connectable: bool | None = None,
    hidden: bool = False,
)

Edge(
    id: str,                        # required
    source: str,                    # required
    target: str,                    # required
    source_handle: str | None = None,
    target_handle: str | None = None,
    type: Literal["bezier","step","smoothstep","straight"] = "bezier",  # REQ-017
    label: str | None = None,
    animated: bool = False,
    marker_start: EdgeMarker | None = None,
    marker_end: EdgeMarker | None = None,
    data: dict = {},
)

Viewport(x: float = 0, y: float = 0, zoom: float = 1)

HandleConfig(id: str, type: Literal["source","target"],
             position: Literal["top","bottom","left","right"])  # REQ-021

EdgeMarker(type: Literal["arrow","arrowclosed"], width: int = 20,
           height: int = 20, color: str | None = None)
```

**Validation (REQ-016):** missing/empty `id`, `position`, `source`, `target` →
`ValueError("Node.position is required")`-style messages at construction time.

## 5. Event payload models

```python
class NodeChange(TypedDict):
    id: str
    type: Literal["position", "dimensions", "select", "remove", "add", "replace"]
    # present per type:
    position: NotRequired[dict]     # {x, y} — type == "position"
    dragging: NotRequired[bool]     # type == "position"
    dimensions: NotRequired[dict]   # {width, height} — type == "dimensions"
    selected: NotRequired[bool]     # type == "select"
    item: NotRequired[dict]         # full node — type in ("add", "replace") only

class EdgeChange(TypedDict):
    id: str
    type: Literal["select", "remove", "add", "replace"]
    selected: NotRequired[bool]
    item: NotRequired[dict]

class Connection(TypedDict):
    source: str
    target: str
    source_handle: str | None
    target_handle: str | None
```

Event specs guarantee: no full node/edge objects in `position`/`dimensions`/`select`/
`remove` changes (REQ-005/006); payload ≤ `max_event_payload_kb` (REQ-013).

## 6. `FlowState` (Layer 3)

```python
class FlowState(rx.ComponentState):
    nodes: list[Node] = []
    edges: list[Edge] = []
    selected_node_ids: list[str] = []
    selected_edge_ids: list[str] = []
    allow_duplicate_edges: bool = False        # REQ-037

    # --- operations (REQ-030) ---
    def add_node(self, node: Node | dict) -> None
    def remove_node(self, node_id: str) -> None        # also removes connected edges
    def add_edge(self, edge: Edge | dict | Connection) -> None
    def remove_edge(self, edge_id: str) -> None
    def update_node_data(self, node_id: str, data: dict, merge: bool = True) -> None
    def clear(self) -> None

    # --- change application (REQ-031/032) ---
    def on_nodes_change(self, changes: list[NodeChange]) -> None
    def on_edges_change(self, changes: list[EdgeChange]) -> None
    def on_connect(self, connection: Connection) -> None
    def on_selection_change(self, payload: dict) -> None

    # --- layout (REQ-033) ---
    def apply_layout(self, algorithm: str = "hierarchical", **options) -> None

    @classmethod
    def get_component(cls, *children, **props) -> rx.Component
```

Behavioral contract:

| Method | Contract |
|---|---|
| `add_node` | Appends; duplicate `id` → `ValueError` |
| `remove_node` | Removes node + incident edges; unknown id → warning, no-op (REQ-032) |
| `add_edge` | From `Edge`/`Connection`; auto-generates `id` (`e{source}-{target}[-{n}]`) if absent; duplicate id → `ValueError`; duplicate `(source, source_handle, target, target_handle)` → skip + warning unless `allow_duplicate_edges` (REQ-037); missing endpoint → warning stating the edge will not render (INV-03) |
| `update_node_data` | `merge=True` shallow-merges into `data`; `merge=False` replaces |
| `on_nodes_change` | Delegates to `apply_node_changes`; unknown ids skipped with warning (REQ-032) |
| `apply_layout` | Mutates node positions server-side; algorithm ∈ {hierarchical, force, circular, layered} |

### Pure helpers

```python
def apply_node_changes(changes: list[NodeChange], nodes: list[Node]) -> list[Node]
def apply_edge_changes(changes: list[EdgeChange], edges: list[Edge]) -> list[Edge]
```

Clean-room Python reimplementation of the xyflow helper semantics from public docs
(REQ-031). Pure functions: new list returned, inputs not mutated.

## 7. Layouts module (Layer 3)

```python
from reflex_react_flow import layouts

layouts.layout_hierarchical(nodes, edges, *, direction="TB", layer_gap=100,
                            node_gap=60, seed=None) -> list[Node]
layouts.layout_force(nodes, edges, *, iterations=50, k=None, seed=42) -> list[Node]
layouts.layout_circular(nodes, edges, *, radius=None, center=(0, 0)) -> list[Node]
layouts.layout_layered(nodes, edges, *, direction="TB", layer_gap=100,
                       node_gap=60) -> list[Node]
```

Contracts:
- Pure functions: return new `Node` lists with updated `position`; never mutate input (REQ-033).
- Deterministic when `seed` provided.
- `direction` ∈ `{"TB","BT","LR","RL"}`.
- Cyclic input to `layout_hierarchical` → cycle-break + warning, no exception (REQ-034).
- Implementation: `networkx` only (BSD-3); `grandalf` only if license verified (PRD §8).

## 8. LangGraph adapter (Layer 3, extra `[langgraph]`)

```python
def from_langgraph(
    compiled_graph,                  # langgraph CompiledStateGraph
    *,
    layout: str | None = "hierarchical",
    status_map: dict[str, str] | None = None,   # node name → agent status
) -> tuple[list[Node], list[Edge]]
```

- Produces `agent_node`-typed nodes (`data.name` = graph node name) and edges from graph transitions; START/END rendered as `io_node` (REQ-035).
- Missing dependency → `ImportError` with `pip install reflex-react-flow[langgraph]` (REQ-036).

## 9. Registry `node.data` contract (Layer 2)

The exact JSON schema per node type is normative in the
[Data Model spec §4](../data-model/reflex-react-flow-schema.md). Contract summary
(REQ-020/021/024):

| Type constant | Value | data keys (all optional unless noted) |
|---|---|---|
| `CARD_NODE` | `"card_node"` | `icon`, `title`, `subtitle`, `badge`, `badge_color`, `handles` |
| `AGENT_NODE` | `"agent_node"` | `name`, `role`, `status` (idle/running/done/error), `tokens`, `calls`, `handles` |
| `GROUP_NODE` | `"group_node"` | `title` |
| `ANNOTATION_NODE` | `"annotation_node"` | `text` (light markdown: bold/italic/code) — no handles ever |
| `IO_NODE` | `"io_node"` | `label`, `kind` ("input"→ single source handle, "output"→ single target handle) |

Unknown `data` keys are ignored by the JSX (forward compatibility). Missing keys →
documented defaults, never a crash (REQ-024).

## 10. Errors

| Condition | Behavior | REQ |
|---|---|---|
| Missing required model field | `ValueError` at construction, field named | REQ-016 |
| Duplicate node/edge id in `FlowState` | `ValueError` | §6 |
| Change for unknown id | skip + `warnings.warn` | REQ-032 |
| Duplicate connection (same handle pair) | skip + `warnings.warn`; opt in via `allow_duplicate_edges` | REQ-037 |
| Unknown node type at render | default node + console warning | REQ-023 |
| Payload > cap | truncate + console warning | REQ-013 |
| Cyclic graph in hierarchical layout | cycle-break + `warnings.warn` | REQ-034 |
| `from_langgraph` without extra | `ImportError` with install hint | REQ-036 |

## 11. Versioning

Semver on the public surface defined in this document. v1 additive changes (new
optional props/keys) are minor; renames/removals are major and require a Delta Spec
in `changes/` (Constitution Art. 9). The registry `node.data` schemas are part of the
public API.

---

## Constitution check
- Art. 3: all naming here uses `reflex_react_flow`/`rxf`; no forbidden names.
- Art. 4: 100% snake_case surface; camelCase confined to the boundary table (§3.1).
- Art. 5: props table is the parity contract; uncovered v12 props are implicitly out of scope and listed in the docs parity table.
- Art. 6: §5 payload models + §3.1 `viewport_debounce_ms`/`max_event_payload_kb` implement the filtered-payload mandate.
- Art. 9: §11 binds this surface to semver + Delta Specs.

## Change History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-08-08 | Initial version |
