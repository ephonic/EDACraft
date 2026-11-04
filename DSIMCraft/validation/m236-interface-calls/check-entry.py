"""Check actual release emissions before rerunning identical validated native inputs."""
from pathlib import Path
import hashlib,json,subprocess,sys
root,entry,out=map(lambda p:Path(p).absolute(),sys.argv[1:4]);out.mkdir(parents=True,exist_ok=True)
release=entry.resolve().parent;receipt=json.loads((release/'release.json').read_text())
assert receipt['status']=='PASS' and receipt['active'] and receipt['git_commit']==subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
report=dict(status='RUNNING',release=str(release),source_commit=receipt['git_commit'],source_sha256=receipt['source_sha256'],native_artifacts_reused_after_cpp_identity=True,models={})
sys.path.insert(0,str(root/'tests/waveform'));from reader import read
try:
 for group in ['virtual_interface_calls','virtual_interfaces']:
  for name,trace in json.loads((root/'tests'/group/'expected.json').read_text()).items():
   w=out/group/name;w.mkdir(parents=True,exist_ok=True);cpp=w/'entry.cpp';validated=release/group/name
   p=subprocess.run(list(map(str,[entry,'--shared-functions',root/'tests'/group/(name+'.sv'),'--wave-support','--emit-only','--emit-cpp',cpp])),cwd=w,capture_output=True,text=True,timeout=600)
   (w/'compile.stdout').write_text(p.stdout);(w/'compile.stderr').write_text(p.stderr);assert not p.returncode,(group,name,p.stderr)
   assert cpp.read_bytes()==(validated/'shared.cpp').read_bytes(),(group,name,'complete native input')
   p=subprocess.run(list(map(str,[validated/'shared','--waveform',w/'entry.vcd','--wave-format','vcd','--wave-mode','ordered'])),cwd=w,capture_output=True,text=True,timeout=600)
   (w/'run.stdout').write_text(p.stdout);(w/'run.stderr').write_text(p.stderr);assert not p.returncode and p.stdout.splitlines()==trace,(group,name,p.stderr)
   assert read(w/'entry.vcd')==read(validated/'shared.vcd'),(group,name,'complete ordered wave')
   report['models'][group+'/'+name]=dict(trace=trace,cpp_sha256=hashlib.sha256(cpp.read_bytes()).hexdigest(),complete_waveform_identity=True)
   print('PASS actual stable entry',group,name,flush=True)
 report['status']='PASS'
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
