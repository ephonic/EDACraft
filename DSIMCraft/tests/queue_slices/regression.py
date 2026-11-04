"""Queue values and zero-time function I/O: VCS traces and complete waves."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
compiler,out=map(lambda p:Path(p).resolve(),sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
fixtures=Path(__file__).resolve().parent;root=fixtures.parents[1]
sys.path.insert(0,str(root/'tests/waveform'));from reader import read
expected=json.loads((fixtures/'expected.json').read_text());report=dict(status='RUNNING',models={},captures=0)
def run(args,w,label,ok=True):
 p=subprocess.run(list(map(str,args)),cwd=w,capture_output=True,text=True,timeout=float(os.getenv('DSIM_TEST_COMMAND_TIMEOUT','600')))
 (w/(label+'.stdout')).write_text(p.stdout);(w/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==(0 if ok else 1),(label,p.returncode,p.stderr[-4000:]);return p
try:
 for name,wanted in expected.items():
  w=out/name;w.mkdir(exist_ok=True);reference=None
  for backend,flags in [('serial',[]),('shared',['--shared-functions']),('wheel',['--shared-functions','--time-wheel'])]:
   run([compiler,*flags,fixtures/(name+'.sv'),'--wave-support','--emit-cpp',w/(backend+'.cpp'),'-o',w/backend],w,backend+'-compile')
   trace=run([w/backend,'--waveform',w/(backend+'.vcd'),'--wave-format','vcd','--wave-mode','ordered'],w,backend+'-run').stdout.splitlines()
   assert trace==wanted,(name,backend,trace,wanted)
   current=read(w/(backend+'.vcd'));report['captures']+=1
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete waveform')
   if name=='file_functions':assert (w/'values.txt').read_bytes()==b'7 8\n9\n'
  report['models'][name]=dict(trace=wanted,source_sha256=hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest())
  print('PASS queue slice',name,flush=True)
 negatives={
  'lhs':('module top;int q[$],r[$];initial q[0:1]=r;endmodule','whole queue destination'),
  'real_bound':('module top;int q[$],r[$];real n;initial r=q[n:1];endmodule','range or index requires integral operands'),
  'scalar':('module top;int q[$],n;initial n=q[0:1];endmodule','matching unpacked array operands'),
  'sort':('module top;int q[$];initial q[0:1].sort();endmodule','writable array storage'),
  'task_in_function':('module top;task t();endtask function int f();t();return 0;endfunction initial $display("%0d",f());endmodule','without task calls'),
 }
 for name,(source,message) in negatives.items():
  w=out/('reject-'+name);w.mkdir(exist_ok=True);(w/'tb.sv').write_text(source);(w/'model.cpp').write_text('protected\n')
  p=run([compiler,w/'tb.sv','--emit-only','--emit-cpp',w/'model.cpp'],w,'compile',False)
  assert message in p.stderr,(name,p.stderr)
  assert (w/'model.cpp').read_text()=='protected\n'
 report.update(status='PASS',negative_cases=len(negatives))
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
