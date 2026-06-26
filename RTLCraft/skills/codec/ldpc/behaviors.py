"""
skills.codec.ldpc.behaviors — Three-Layer Behavioral Models (Shim)
Layer 1: functional — combinatorial models
Layer 2: cycle_level — register-accurate models
Layer 3: layer3_dsl/ — one file per DSL Module class
"""
from __future__ import annotations

from skills.codec.ldpc.functional import *
from skills.codec.ldpc.cycle_level import *
