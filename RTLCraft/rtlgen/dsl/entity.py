"""Minimal local entity base for the current DSL kernel."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IREntity:
    """Small subset of the old entity API without contract-system coupling."""

    name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    _constraints: List[Any] = field(default_factory=list)

    def add_tag(self, tag: str) -> "IREntity":
        if tag not in self.tags:
            self.tags.append(tag)
        return self

    def set_metadata(self, **kwargs: Any) -> "IREntity":
        self.metadata.update(kwargs)
        return self

    def add_constraint(self, constraint: Any) -> "IREntity":
        self._constraints.append(constraint)
        return self

    def constraints(self) -> List[Any]:
        return list(self._constraints)

    def constraints_by(
        self,
        *,
        layer: Optional[str] = None,
        category: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> List[Any]:
        result = []
        for constraint in self._constraints:
            if layer is not None and getattr(constraint, "layer", None) != layer:
                continue
            if category is not None and getattr(constraint, "category", None) != category:
                continue
            if owner is not None and getattr(constraint, "owner", None) != owner:
                continue
            result.append(constraint)
        return result
