"""Sanitized full-library frontend and native UVM sequence/driver integration."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys
root,compiler,library,normal,out=map(lambda p:Path(p).resolve(),sys.argv[1:6]);out.mkdir(parents=True,exist_ok=True)
environment=os.environ|{'ASAN_OPTIONS':'detect_leaks=0:symbolize=0'}
previous=json.loads((normal/'results.json').read_text());assert previous['status']=='PASS'
report=dict(status='RUNNING',complete_uvm_source=True,frontend_sanitized=True,native_sanitized=True,native_optimization='-O0',uvm_source_tree_sha256=previous['uvm_source_tree_sha256'],test_sha256=previous['smoke_sha256'])
try:
 commands=[('frontend',['/bin/bash','-c','ulimit -s 65520; exec "$@"','dsim-uvm-asan',compiler,'--shared-functions','+incdir+'+str(library/'src'),'+define+UVM_NO_DPI',library/'src/uvm_pkg.sv',root/'tests/uvm_preprocess/packing.sv','--emit-only','--emit-cpp',out/'model.cpp']),('compile',['/usr/bin/clang++','-std=c++17','-O0','-gline-tables-only','-fsanitize=address,undefined','-fno-omit-frame-pointer',out/'model.cpp','-o',out/'native','-Wl,-export_dynamic','-I/opt/homebrew/include','/opt/homebrew/lib/libz3.dylib']),('run',[out/'native'])]
 for label,args in commands:
  p=subprocess.run(list(map(str,args)),cwd=out,capture_output=True,text=True,env=environment,timeout=1200)
  (out/(label+'.stdout')).write_text(p.stdout);(out/(label+'.stderr')).write_text(p.stderr)
  assert not p.returncode and 'ERROR: AddressSanitizer' not in p.stderr and 'runtime error:' not in p.stderr,(label,p.returncode,p.stderr[-4000:])
  if label=='frontend':assert (out/'model.cpp').read_bytes()==(normal/'model.cpp').read_bytes(),'complete generated UVM C++ identity'
  print('PASS full UVM sanitized',label,flush=True)
 assert 'TRACE REAL_UVM_SMOKE PACKING 8196 8196' in p.stdout
 assert all(re.search(r'\b'+severity+r'\s*:\s*0\b',p.stdout) for severity in ['UVM_ERROR','UVM_FATAL'])
 report.update(status='PASS',hello_pass=True,complete_cpp_identity=True,cpp_sha256=hashlib.sha256((out/'model.cpp').read_bytes()).hexdigest())
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
