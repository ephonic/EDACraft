"""Replay actual generated checks across an active setup/hold window."""
from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parents[2]
subprocess.run([sys.executable,str(root/'tests/sdf_runtime/checkpoint.py'),sys.argv[1],sys.argv[2],'setuphold','width','edge-overrides','composed'],check=True)
