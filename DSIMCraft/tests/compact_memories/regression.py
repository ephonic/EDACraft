from pathlib import Path
import hashlib,json,subprocess,sys,time
from cases import make,EXPECTED
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();make(out)
report=dict(status='RUNNING',models={})
try:
 for name,expected in EXPECTED.items():
  work=out/name
  for label,command in [('compile',[compiler,'--compact-memories','--top','top',work/'tb.sv','--emit-cpp',work/'model.cpp','-o',work/'native']),('run',[work/'native'])]:
   command=list(map(str,command));start=time.monotonic();p=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=180)
   (work/(label+'.command.json')).write_text(json.dumps(command)+'\n');(work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
   assert p.returncode==0,(name,label,p.stdout,p.stderr[-3000:])
   if label=='run':
    trace=[s for s in p.stdout.splitlines() if s.startswith('TRACE')];assert trace==expected,(name,trace,expected)
  assert (work/'model.cpp').stat().st_size<2000000,'per-element generated storage returned'
  code=(work/'model.cpp').read_text();assert code.count('\ns.run();\n')==1
  replay=code.replace('\ns.run();\n','\nif(s.predict_until(3,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("unexpected prediction commit");\nif(s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing rollback");\ns.run();\n')
  (work/'replay.cpp').write_text(replay)
  command=['c++','-std=c++17','-O1',str(work/'replay.cpp'),'-o',str(work/'replay')]
  p=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=180)
  (work/'replay-compile.stderr').write_text(p.stderr);assert p.returncode==0,p.stderr[-2000:]
  p=subprocess.run([str(work/'replay')],cwd=work,capture_output=True,text=True,timeout=30)
  (work/'replay.stdout').write_text(p.stdout);(work/'replay.stderr').write_text(p.stderr)
  assert p.returncode==0 and p.stdout==(work/'run.stdout').read_text(),(name,p.returncode,p.stdout,p.stderr)
  report['models'][name]=dict(status='PASS',source_sha256=hashlib.sha256((work/'tb.sv').read_bytes()).hexdigest(),trace=trace,cpp_bytes=(work/'model.cpp').stat().st_size)
  print('PASS compact',name,flush=True)
 report['status']='POSITIVE_PASS'
finally:
 (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
# Unsupported representations must fail before replacing an existing model.
rejects={
 'copy':('reg [7:0] a[0:1023],b[0:1023];initial a=b;',[], 'compact large memories currently support element access'),
 'ref':('reg [7:0] a[0:1023];task automatic f(ref reg [7:0] x);x=1;endtask initial f(a[2]);',[],'ref to a compact fixed array element'),
 'wave':('reg [7:0] a[0:1023];',['--wave-support'],'requires serial simulation without waveform support'),
 'parallel':('reg [7:0] a[0:1023];',['--threads','2'],'requires serial simulation without waveform support')
}
for name,(body,flags,diagnostic) in rejects.items():
 work=out/name;work.mkdir(exist_ok=True);(work/'tb.sv').write_text('module top;'+body+'endmodule\n')
 cpp=work/'model.cpp';cpp.write_text('preserve existing model\n')
 p=subprocess.run([str(compiler),'--compact-memories','--emit-only','--emit-cpp',str(cpp),*flags,str(work/'tb.sv')],cwd=work,capture_output=True,text=True,timeout=30)
 (work/'reject.stderr').write_text(p.stderr)
 assert p.returncode==1 and diagnostic in p.stderr,(name,p.returncode,p.stderr)
 assert cpp.read_text()=='preserve existing model\n'
report['status']='PASS';report['rejections']=len(rejects);(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
