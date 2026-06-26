"""
skills.codec.video.behaviors — Three-Layer Behavioral Models (Shim)
Layer 1: functional — combinatorial models
Layer 2: cycle_level — register-accurate models
Layer 3: layer3_dsl/ — one file per DSL Module class
"""
from __future__ import annotations

from skills.codec.video.functional import *
from skills.codec.video.cycle_level import *
