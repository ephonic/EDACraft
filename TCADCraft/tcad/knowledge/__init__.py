"""D3+D4 law library (plan0619.md §D3+D4).

Maps structural triggers to hard physical constraints that gate the search
before the expensive solver runs.  See :mod:`tcad.knowledge.law_engine`.
"""

from .law_engine import (
    Law, load_laws, check_law, check_all_laws, extract_geometry,
)

__all__ = [
    "Law", "load_laws", "check_law", "check_all_laws", "extract_geometry",
]
