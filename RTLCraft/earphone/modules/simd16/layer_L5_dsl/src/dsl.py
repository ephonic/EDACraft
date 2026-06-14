"""L5 DSL module for the EarphoneSIMD16 accelerator.

This module re-exports the RTL-ready DSL class from the legacy monolithic
entry point.  The long-term goal is to host the full ``EarphoneSIMD16``
class locally as part of the document-driven refactoring.
"""

from __future__ import annotations

from earphone.design_earphone import EarphoneSIMD16

__all__ = ["EarphoneSIMD16"]
