"""Finish identity checks after both independently launched suites complete."""
from pathlib import Path
import hashlib,json,sys
root,sanitized,normal,out=map(lambda p:Path(p).resolve(),sys.argv[1:5]);out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(root/'tests/waveform'));from reader import read
expected=json.loads((root/'tests/virtual_interface_calls/expected.json').read_text())
original=json.loads((sanitized/'results.json').read_text())
report=dict(status='RUNNING',models={},frontend_sanitized=True,native_sanitized=True,completed_identity_checks=True)
try:
 for name in ['capture','reentry','arguments','types','arrays','timing','static']:
  work=sanitized/name
  for label in ['compile','run']:
   errors=(work/(label+'.stderr')).read_text()
   assert 'ERROR: AddressSanitizer' not in errors and 'runtime error:' not in errors,(name,label,errors)
  assert (work/'run.stdout').read_text().splitlines()==expected[name],name
  assert (work/'model.cpp').read_bytes()==(normal/name/'shared.cpp').read_bytes(),(name,'complete generated C++')
  assert original['models'][name]['cpp_sha256']==hashlib.sha256((work/'model.cpp').read_bytes()).hexdigest(),(name,'original successful frontend/native execution')
  assert read(work/'model.vcd')==read(normal/name/'shared.vcd'),(name,'complete ordered waveform')
  report['models'][name]=dict(trace=expected[name],cpp_sha256=hashlib.sha256((work/'model.cpp').read_bytes()).hexdigest())
 report['status']='PASS'
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
