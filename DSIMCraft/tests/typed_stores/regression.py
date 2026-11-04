"""Verify fixed-width stores against the original complete publication path."""
from pathlib import Path
import runpy,sys
sys.argv.append('--typed-stores')
runpy.run_path(str(Path(__file__).resolve().parents[1]/'comb_leaves/regression.py'),run_name='__main__')
