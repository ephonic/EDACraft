"""Exercise native process activations with the shared scheduling oracle."""
from pathlib import Path
import runpy,sys
sys.argv.append('--compiled-activation')
runpy.run_path(str(Path(__file__).resolve().parents[1]/'comb_leaves/regression.py'),run_name='__main__')
