from pathlib import Path
import runpy,sys
sys.argv.append('runtime_array_patterns')
runpy.run_path(str(Path(__file__).resolve().parents[1]/"typed_execution.py"),run_name="__main__")
