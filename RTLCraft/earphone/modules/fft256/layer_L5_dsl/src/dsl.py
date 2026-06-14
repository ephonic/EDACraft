"""L5 DSL module for the EarphoneFFT256 accelerator.

Re-exports the RTL-ready DSL class from the legacy monolithic entry point.
"""

from __future__ import annotations

from earphone.design_earphone import EarphoneFFT256

__all__ = ["EarphoneFFT256"]
