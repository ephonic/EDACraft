"""Check the sanitized frontend and actual generated native programs."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root,compiler,out=map(lambda p:Path(p).resolve(),sys.argv[1:4]);out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(root/'tests/waveform'));from reader import read
environment=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:symbolize=0')
expected=json.loads((root/'tests/virtual_interface_calls/expected.json').read_text());expected={k:expected[k] for k in ['capture']};report=dict(status='RUNNING',models={},frontend_sanitized=True,native_sanitized=True)
try:
 for name,wanted in expected.items():
  w=out/name;w.mkdir(exist_ok=True)
  commands=[('compile',['/bin/bash','-c','ulimit -s 65520; exec "$@"','dsim-asan',compiler,'--shared-functions',root/'tests/virtual_interface_calls'/(name+'.sv'),'--wave-support','--cxx-flag','-O1','--cxx-flag','-g','--cxx-flag','-fsanitize=address,undefined','--cxx-flag','-fno-omit-frame-pointer','--emit-cpp',w/'model.cpp','-o',w/'native']),('run',[w/'native','--waveform',w/'model.vcd','--wave-format','vcd','--wave-mode','ordered'])]
  for label,args in commands:
   p=subprocess.run(list(map(str,args)),cwd=w,capture_output=True,text=True,env=environment,timeout=600)
   (w/(label+'.stdout')).write_text(p.stdout);(w/(label+'.stderr')).write_text(p.stderr)
   assert not p.returncode and 'runtime error:' not in p.stderr and 'ERROR: AddressSanitizer' not in p.stderr,(name,label,p.stderr[-3000:])
  assert p.stdout.splitlines()==wanted,(name,p.stdout,wanted)
  report['models'][name]=dict(trace=wanted,cpp_sha256=hashlib.sha256((w/'model.cpp').read_bytes()).hexdigest())
  print('PASS ASan/UBSan',name,flush=True)
 report['status']='PASS'
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
