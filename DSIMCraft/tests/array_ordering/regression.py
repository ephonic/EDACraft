"""Exercise array ordering, key types, storage aliases and prediction rollback."""
from pathlib import Path
import runpy,sys
sys.argv.append("array_ordering")
runpy.run_path(str(Path(__file__).resolve().parents[1]/"typed_execution.py"),run_name="__main__")
