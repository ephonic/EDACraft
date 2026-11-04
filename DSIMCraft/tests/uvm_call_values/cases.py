from pathlib import Path
import json
FIXTURES=Path(__file__).resolve().parent
EXPECTED=json.loads((FIXTURES/'expected.json').read_text())
def make(out):
 out.mkdir(parents=True,exist_ok=True)
 for name in EXPECTED:
  work=out/name;work.mkdir(exist_ok=True);(work/'tb.sv').write_bytes((FIXTURES/(name+'.sv')).read_bytes())
