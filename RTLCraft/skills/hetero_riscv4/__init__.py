"""skills.hetero_riscv4 — Heterogeneous 4-Core RISC-V SoC (2 big + 2 little).

big.LITTLE-style design: 2 performance cores + 2 efficiency cores
connected via 2x2 NoC mesh with directory-based MSI cache coherence.
"""
from .dsl_modules import *
from .models import *
from .behaviors import *
from .arch_templates import *
from .skeleton_templates import *
