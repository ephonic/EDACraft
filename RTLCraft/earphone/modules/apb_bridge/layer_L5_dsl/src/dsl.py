"""L5 DSL module for the EarphoneAPBBridge.

Re-exports the RTL-ready DSL class from the legacy monolithic entry point.
"""

from __future__ import annotations

from earphone.design_earphone import EarphoneAPBBridge

__all__ = ["EarphoneAPBBridge"]
