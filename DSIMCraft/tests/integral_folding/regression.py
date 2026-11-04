"""Keep runtime values out of the integral constant-function interpreter."""
from pathlib import Path
import runpy,sys
sys.argv.append("integral_folding")
runpy.run_path(str(Path(__file__).resolve().parents[1]/"typed_execution.py"),run_name="__main__")
