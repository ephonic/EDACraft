"""riscv_ooo_7nm — High-performance out-of-order RISC-V core on 7nm.

Architecture:
  - 8-wide fetch, 6-wide decode/rename/dispatch/commit
  - 256-entry ROB, 192 physical registers, 4 ALU pipes
  - 2 load pipes, 2 store pipes, 4 FPU pipes
  - 48-entry instruction buffer, 16-entry issue queues
  - 7nm, 2GHz target frequency
  - TAGE-SC branch predictor + BTB + RAS
"""

from skills.riscv_ooo_7nm.params import ooo_7nm_params
from skills.riscv_ooo_7nm.arch_templates import build_ooo_arch
