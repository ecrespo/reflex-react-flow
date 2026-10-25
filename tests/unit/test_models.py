"""T-004 — data model tests (Data Model spec §2).

Covers REQ-016 (construction validation), REQ-017 (edge types/markers/labels) and
REQ-021 (HandleConfig shape), plus invariants INV-05 and INV-06.
"""

from __future__ import annotations

import math

import pytest
from reflex_react_flow.models import Edge, EdgeMarker, HandleConfig, Node, Viewport

# --------------------------------------------------------------------------
# Node — required fields and validation (REQ-016)
# --------------------------------------------------------------------------


def test_node_requires_non_empty_id() -> None:
    """REQ-016: empty `id` raises ValueError naming the field."""
    with pytest.raises(ValueError, match=r"Node\.id"):
        Node(id="", position=(0, 0))


def test_node_requires_position() -> None:
    """REQ-016: missing `position` raises ValueError naming the field."""
    with pytest.raises(ValueError, match=r"Node\.position"):
        Node(id="n1", position=None)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_node_rejects_non_finite_coordinates(bad: float) -> None:
    """REQ-016 / Data Model §6: NaN and Infinity are not JSON numbers."""
    with pytest.raises(ValueError, match=r"Node\.position"):
        Node(id="n1", position=(bad, 0))


def test_node_accepts_tuple_or_dict_position() -> None:
    """API Spec §4: `position` accepts a tuple or a {x, y} dict."""
    assert Node(id="a", position=(1, 2)).position == {"x": 1.0, "y": 2.0}
    assert Node(id="b", position={"x": 3, "y": 4}).position == {"x": 3.0, "y": 4.0}


def test_node_defaults() -> None:
    """Data Model §2.1: type defaults to 'default', data to {}, hidden to False."""
    node = Node(id="n1", position=(0, 0))
    assert node.type == "default"
    assert node.data == {}
    assert node.hidden is False
    assert node.parent_id is None


def test_node_rejects_non_positive_dimensions() -> None:
    """Data Model §2.1: width/height must be > 0 when present."""
    with pytest.raises(ValueError, match=r"Node\.width"):
        Node(id="n1", position=(0, 0), width=0)


def test_extent_parent_requires_parent_id() -> None:
    """INV-05: `extent="parent"` without `parent_id` is invalid."""
    with pytest.raises(ValueError, match="parent_id"):
        Node(id="child", position=(0, 0), extent="parent")


def test_extent_parent_with_parent_id_is_valid() -> None:
    """INV-05: the same node is valid once `parent_id` is supplied."""
    node = Node(id="child", position=(0, 0), extent="parent", parent_id="g1")
    assert node.parent_id == "g1"


# --------------------------------------------------------------------------
# Node — serialization (Data Model §2.1, §6)
# --------------------------------------------------------------------------


def test_node_to_dict_uses_camel_case_keys_and_omits_absent() -> None:
    """Data Model §2.1/§6: parentId camelised; absent optionals are omitted entirely."""
    node = Node(id="c", position=(1, 2), parent_id="g", extent="parent")
    payload = node.to_dict()

    assert payload["parentId"] == "g"
    assert payload["position"] == {"x": 1.0, "y": 2.0}
    assert "parent_id" not in payload
    for absent in ("width", "height", "draggable", "selectable", "connectable"):
        assert absent not in payload


def test_node_round_trip() -> None:
    """Data Model §6: `Node.from_dict(node.to_dict()) == node`."""
    node = Node(
        id="n1",
        position=(10, 20),
        type="card_node",
        data={"title": "T"},
        width=120,
        height=60,
        hidden=True,
        draggable=False,
    )
    assert Node.from_dict(node.to_dict()) == node


def test_node_handles_are_validated(  # REQ-021
) -> None:
    """REQ-021 / INV-06: duplicate handle ids inside one node raise ValueError."""
    with pytest.raises(ValueError, match="handle"):
        Node(
            id="n1",
            position=(0, 0),
            data={
                "handles": [
                    {"id": "a", "type": "source", "position": "left"},
                    {"id": "a", "type": "target", "position": "right"},
                ]
            },
        )


# --------------------------------------------------------------------------
# Edge — validation and types (REQ-016, REQ-017)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["id", "source", "target"])
def test_edge_requires_core_fields(field: str) -> None:
    """REQ-016: missing id/source/target raises ValueError naming the field."""
    kwargs = {"id": "e1", "source": "a", "target": "b"}
    kwargs[field] = ""
    with pytest.raises(ValueError, match=rf"Edge\.{field}"):
        Edge(**kwargs)


def test_edge_defaults_to_bezier() -> None:
    """REQ-017: default edge type is bezier; animated defaults to False."""
    edge = Edge(id="e1", source="a", target="b")
    assert edge.type == "bezier"
    assert edge.animated is False


@pytest.mark.parametrize("edge_type", ["bezier", "step", "smoothstep", "straight"])
def test_edge_accepts_all_specified_types(edge_type: str) -> None:
    """REQ-017: the four v12 edge types are accepted."""
    assert Edge(id="e1", source="a", target="b", type=edge_type).type == edge_type


def test_edge_rejects_unknown_type() -> None:
    """REQ-017: an unspecified edge type is rejected at construction."""
    with pytest.raises(ValueError, match=r"Edge\.type"):
        Edge(id="e1", source="a", target="b", type="spiral")


def test_edge_to_dict_camelises_handles_and_markers() -> None:
    """REQ-017 / Data Model §2.2: handles and markers camelise correctly."""
    edge = Edge(
        id="e1",
        source="a",
        target="b",
        source_handle="out",
        target_handle="in",
        label="flows to",
        marker_end=EdgeMarker(type="arrowclosed", color="#f00"),
    )
    payload = edge.to_dict()

    assert payload["sourceHandle"] == "out"
    assert payload["targetHandle"] == "in"
    assert payload["label"] == "flows to"
    assert payload["markerEnd"] == {
        "type": "arrowclosed",
        "width": 20,
        "height": 20,
        "color": "#f00",
    }
    assert "markerStart" not in payload


def test_edge_round_trip() -> None:
    """Data Model §6: Edge survives a to_dict/from_dict round trip."""
    edge = Edge(
        id="e1",
        source="a",
        target="b",
        type="smoothstep",
        label="x",
        animated=True,
        marker_start=EdgeMarker(type="arrow"),
    )
    assert Edge.from_dict(edge.to_dict()) == edge


# --------------------------------------------------------------------------
# HandleConfig (REQ-021)
# --------------------------------------------------------------------------


def test_handle_config_requires_valid_type_and_position() -> None:
    """REQ-021: handle `type` and `position` are constrained enums."""
    with pytest.raises(ValueError, match=r"HandleConfig\.type"):
        HandleConfig(id="h", type="sideways", position="left")
    with pytest.raises(ValueError, match=r"HandleConfig\.position"):
        HandleConfig(id="h", type="source", position="northwest")


def test_handle_config_requires_id() -> None:
    """REQ-021: an empty handle id is invalid."""
    with pytest.raises(ValueError, match=r"HandleConfig\.id"):
        HandleConfig(id="", type="source", position="left")


def test_handle_config_round_trip() -> None:
    """REQ-021: HandleConfig serializes to the §2.5 shape."""
    handle = HandleConfig(id="out", type="source", position="right")
    assert handle.to_dict() == {"id": "out", "type": "source", "position": "right"}
    assert HandleConfig.from_dict(handle.to_dict()) == handle


# --------------------------------------------------------------------------
# Viewport and EdgeMarker (Data Model §2.3, §2.4)
# --------------------------------------------------------------------------


def test_viewport_defaults_and_round_trip() -> None:
    """Data Model §2.3: viewport defaults to origin at zoom 1."""
    viewport = Viewport()
    assert viewport.to_dict() == {"x": 0.0, "y": 0.0, "zoom": 1.0}
    assert Viewport.from_dict({"x": 5, "y": 6, "zoom": 2}) == Viewport(x=5, y=6, zoom=2)


def test_viewport_rejects_non_positive_zoom() -> None:
    """Data Model §2.3: zoom must be a positive finite number."""
    with pytest.raises(ValueError, match=r"Viewport\.zoom"):
        Viewport(zoom=0)


def test_edge_marker_requires_known_type() -> None:
    """Data Model §2.4: marker type is arrow or arrowclosed."""
    with pytest.raises(ValueError, match=r"EdgeMarker\.type"):
        EdgeMarker(type="diamond")


def test_edge_marker_defaults() -> None:
    """Data Model §2.4: width/height default to 20; color is omitted when absent."""
    assert EdgeMarker(type="arrow").to_dict() == {"type": "arrow", "width": 20, "height": 20}
