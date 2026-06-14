"""L5 DSL module for the EarphoneQSPI controller.

Re-exports the RTL-ready DSL class from the legacy monolithic entry point.
"""

from __future__ import annotations

from earphone.design_earphone import EarphoneQSPI

__all__ = ["EarphoneQSPI"]
