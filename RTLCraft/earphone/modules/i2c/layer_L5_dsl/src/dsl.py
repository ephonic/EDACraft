"""L5 DSL module for the EarphoneI2C controller.

Re-exports the RTL-ready DSL class from the legacy monolithic entry point.
"""

from __future__ import annotations

from earphone.design_earphone import EarphoneI2C

__all__ = ["EarphoneI2C"]
