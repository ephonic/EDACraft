"""
Design Compiler Stage Configuration — standalone, YAML-loadable.

This is a re-export of SynthesisConfig for the config layer.
The script generator in src/tools/dc_adapter.py consumes this.
"""
from __future__ import annotations

from ..db.design_state import SynthesisConfig as DCStageConfig
