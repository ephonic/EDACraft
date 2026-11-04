"""Reuse actual generated-program transaction checks on wire-delay contexts."""
from pathlib import Path
import json
import subprocess
import sys

root=Path(__file__).resolve().parents[2]
report=json.loads((Path(sys.argv[2])/'results.json').read_text())
assert report['status']=='PASS'
base=Path(report['run_directory'])/'basic'
subprocess.run([sys.executable,str(root/'tests/sdf_runtime/checkpoint.py'),sys.argv[1],str(base),
                'fanout','pulses','input-and-output','multi-driver'],check=True)
