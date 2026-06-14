"""L5 DSL module for the EarphoneSRAM256K memory.

Re-exports the RTL-ready DSL class from the legacy monolithic entry point.
"""

from __future__ import annotations

from earphone.design_earphone import EarphoneSRAM256K

__all__ = ["EarphoneSRAM256K"]
