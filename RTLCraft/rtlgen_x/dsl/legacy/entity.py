"""Minimal local entity base for the imported legacy DSL kernel."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class IREntity:
    """Small subset of the old entity API without contract-system coupling."""

    name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def add_tag(self, tag: str) -> "IREntity":
        if tag not in self.tags:
            self.tags.append(tag)
        return self

    def set_metadata(self, **kwargs: Any) -> "IREntity":
        self.metadata.update(kwargs)
        return self
