"""L5 DSL module for the EarphoneRV32 core.

This module currently re-exports the EarphoneRV32 RTL implementation from the
legacy monolithic entry point.  It will be progressively migrated to contain
the full DSL definition locally as part of the document-driven refactoring.
"""

from __future__ import annotations

# Re-export during migration; the long-term goal is to host the full
# EarphoneRV32 class in this file.
from earphone.design_earphone import EarphoneRV32

__all__ = ["EarphoneRV32"]
