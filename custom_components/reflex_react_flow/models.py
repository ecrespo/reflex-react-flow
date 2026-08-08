"""Serializable structures that cross the Python <-> browser boundary.

Normative schemas live in ``specs/data-model/reflex-react-flow-schema.md``. These are
plain dataclasses: they hold no framework state and import nothing from Reflex, so
Layer 1 shape and validation stay testable without a running app (Tech Design §5.2.1,
DIP).

Python fields are snake_case; :meth:`to_dict` camelises them at the boundary and
nowhere else (Constitution Art. 4).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, fields
from typing import Any, ClassVar

__all__ = ["Edge", "EdgeMarker", "HandleConfig", "Node", "Viewport"]

EDGE_TYPES = ("bezier", "step", "smoothstep", "straight")
MARKER_TYPES = ("arrow", "arrowclosed")
HANDLE_TYPES = ("source", "target")
HANDLE_POSITIONS = ("top", "bottom", "left", "right")


# --------------------------------------------------------------------------
# validation helpers — one implementation per rule (DRY, Tech Design §5.2.1)
# --------------------------------------------------------------------------


def _require_text(value: Any, qualified_name: str) -> str:
    """Return `value` as a non-empty string or raise naming the field (REQ-016)."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{qualified_name} is required and must be a non-empty string")
    return value


def _require_finite(value: Any, qualified_name: str) -> float:
    """Return `value` as a finite float or raise naming the field.

    NaN and +/-Infinity are excluded because they are not representable as JSON
    numbers (Data Model §6).
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{qualified_name} must be a number, got {value!r}") from None
    if not math.isfinite(number):
        raise ValueError(f"{qualified_name} must be finite, got {value!r}")
    return number


def _require_choice(value: Any, allowed: tuple[str, ...], qualified_name: str) -> str:
    """Return `value` if it is one of `allowed`, else raise naming the field."""
    if value not in allowed:
        raise ValueError(f"{qualified_name} must be one of {allowed}, got {value!r}")
    return value


def _to_camel(name: str) -> str:
    """Translate a snake_case field name to its camelCase JSON key."""
    head, *rest = name.split("_")
    return head + "".join(word[:1].upper() + word[1:] for word in rest)


# --------------------------------------------------------------------------
# serialization base — single to_dict/from_dict path for every model (Factory)
# --------------------------------------------------------------------------


@dataclass
class _Model:
    """Shared camelCase serialization for the boundary models.

    Subclasses declare two class-level hints:

    ``_OMIT_WHEN_NONE``  fields dropped from the payload when unset (the Data Model
                         spells these as "absent" rather than ``null``).
    ``_NESTED``          field name -> model class, for values that are themselves
                         models and must be (de)serialized recursively.
    """

    _OMIT_WHEN_NONE: ClassVar[frozenset[str]] = frozenset()
    _NESTED: ClassVar[dict[str, type[_Model]]] = {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the JSON shape defined in the Data Model spec."""
        payload: dict[str, Any] = {}
        for spec in fields(self):
            value = getattr(self, spec.name)
            if value is None and spec.name in self._OMIT_WHEN_NONE:
                continue
            if isinstance(value, _Model):
                value = value.to_dict()
            payload[_to_camel(spec.name)] = value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Any:
        """Rebuild a model from its serialized form (inverse of :meth:`to_dict`)."""
        kwargs: dict[str, Any] = {}
        for spec in fields(cls):
            key = _to_camel(spec.name)
            if key not in payload:
                continue
            value = payload[key]
            nested = cls._NESTED.get(spec.name)
            if nested is not None and isinstance(value, dict):
                value = nested.from_dict(value)
            kwargs[spec.name] = value
        return cls(**kwargs)


# --------------------------------------------------------------------------
# leaf models
# --------------------------------------------------------------------------


@dataclass
class HandleConfig(_Model):
    """A connection point on a node (Data Model §2.5, REQ-021)."""

    id: str
    type: str
    position: str

    def __post_init__(self) -> None:
        """Validate the handle id and its constrained enums (REQ-021)."""
        self.id = _require_text(self.id, "HandleConfig.id")
        self.type = _require_choice(self.type, HANDLE_TYPES, "HandleConfig.type")
        self.position = _require_choice(self.position, HANDLE_POSITIONS, "HandleConfig.position")


@dataclass
class EdgeMarker(_Model):
    """An arrow head at one end of an edge (Data Model §2.4, REQ-017)."""

    _OMIT_WHEN_NONE: ClassVar[frozenset[str]] = frozenset({"color"})

    type: str
    width: int = 20
    height: int = 20
    color: str | None = None

    def __post_init__(self) -> None:
        """Validate the marker type (REQ-017)."""
        self.type = _require_choice(self.type, MARKER_TYPES, "EdgeMarker.type")


@dataclass
class Viewport(_Model):
    """Canvas pan/zoom state (Data Model §2.3)."""

    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0

    def __post_init__(self) -> None:
        """Validate coordinates are finite and zoom is positive."""
        self.x = _require_finite(self.x, "Viewport.x")
        self.y = _require_finite(self.y, "Viewport.y")
        self.zoom = _require_finite(self.zoom, "Viewport.zoom")
        if self.zoom <= 0:
            raise ValueError(f"Viewport.zoom must be positive, got {self.zoom!r}")


# --------------------------------------------------------------------------
# graph models
# --------------------------------------------------------------------------


@dataclass
class Node(_Model):
    """One canvas node (Data Model §2.1)."""

    _OMIT_WHEN_NONE: ClassVar[frozenset[str]] = frozenset(
        {"parent_id", "extent", "width", "height", "draggable", "selectable", "connectable"}
    )

    id: str
    position: Any
    type: str = "default"
    data: dict[str, Any] = field(default_factory=dict)
    parent_id: str | None = None
    extent: Any = None
    width: float | None = None
    height: float | None = None
    draggable: bool | None = None
    selectable: bool | None = None
    connectable: bool | None = None
    hidden: bool = False

    def __post_init__(self) -> None:
        """Validate required fields, dimensions, subflow rules and handles (REQ-016)."""
        self.id = _require_text(self.id, "Node.id")
        self.position = _normalise_position(self.position, "Node.position")

        for dimension in ("width", "height"):
            value = getattr(self, dimension)
            if value is not None:
                number = _require_finite(value, f"Node.{dimension}")
                if number <= 0:
                    raise ValueError(f"Node.{dimension} must be > 0, got {value!r}")
                setattr(self, dimension, number)

        # INV-05: a node clamped to its parent must name that parent.
        if self.extent == "parent" and not self.parent_id:
            raise ValueError('Node.extent="parent" requires parent_id to be set (INV-05)')

        _validate_handles(self.data)


@dataclass
class Edge(_Model):
    """A connection between two nodes (Data Model §2.2)."""

    _OMIT_WHEN_NONE: ClassVar[frozenset[str]] = frozenset(
        {"source_handle", "target_handle", "label", "marker_start", "marker_end"}
    )
    _NESTED: ClassVar[dict[str, type[_Model]]] = {
        "marker_start": EdgeMarker,
        "marker_end": EdgeMarker,
    }

    id: str
    source: str
    target: str
    source_handle: str | None = None
    target_handle: str | None = None
    type: str = "bezier"
    label: str | None = None
    animated: bool = False
    marker_start: EdgeMarker | None = None
    marker_end: EdgeMarker | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate endpoints and the edge type (REQ-016, REQ-017)."""
        self.id = _require_text(self.id, "Edge.id")
        self.source = _require_text(self.source, "Edge.source")
        self.target = _require_text(self.target, "Edge.target")
        self.type = _require_choice(self.type, EDGE_TYPES, "Edge.type")


# --------------------------------------------------------------------------
# shared field logic
# --------------------------------------------------------------------------


def _normalise_position(value: Any, qualified_name: str) -> dict[str, float]:
    """Coerce a tuple/list/dict position into ``{"x": float, "y": float}``.

    Accepting both shapes is an API-Spec §4 affordance; storing exactly one shape
    keeps every downstream consumer free of coordinate-format branching.
    """
    if isinstance(value, dict):
        if "x" not in value or "y" not in value:
            raise ValueError(f"{qualified_name} requires both 'x' and 'y', got {value!r}")
        raw_x, raw_y = value["x"], value["y"]
    elif isinstance(value, (tuple, list)) and len(value) == 2:
        raw_x, raw_y = value
    else:
        raise ValueError(
            f"{qualified_name} is required as (x, y) or {{'x': ..., 'y': ...}}, got {value!r}"
        )
    return {
        "x": _require_finite(raw_x, qualified_name),
        "y": _require_finite(raw_y, qualified_name),
    }


def _validate_handles(data: dict[str, Any]) -> None:
    """Enforce unique handle ids within one node (REQ-021, INV-06)."""
    handles = data.get("handles") if isinstance(data, dict) else None
    if not handles:
        return

    seen: set[str] = set()
    for entry in handles:
        handle = HandleConfig.from_dict(entry) if isinstance(entry, dict) else entry
        if not isinstance(handle, HandleConfig):
            raise ValueError(f"Node.data.handles entries must be HandleConfig, got {entry!r}")
        if handle.id in seen:
            raise ValueError(f"Node.data.handles contains a duplicate handle id {handle.id!r}")
        seen.add(handle.id)
