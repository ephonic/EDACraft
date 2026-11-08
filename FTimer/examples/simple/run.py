from pathlib import Path
from ftimer import FTimer
root = Path(__file__).resolve().parent
timer = FTimer(liberty=root / "cells.lib", verilog=root / "design.v", sdc=root / "design.sdc")
print(timer.report_timing(max_paths=5, min_paths=5))
