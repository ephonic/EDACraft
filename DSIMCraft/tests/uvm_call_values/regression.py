"""UVM call/escape semantics, shared function frames and exact wave replay."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
from cases import EXPECTED, make
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tests/waveform'))
from reader import read,declarations
compiler,out=map(lambda p:Path(p).resolve(),sys.argv[1:3]);make(out)
config={s.split('=',1)[0].split(':',1)[0]:s.split('=',1)[1] for s in (compiler.parent/'CMakeCache.txt').read_text().splitlines() if '=' in s and not s.startswith('//')}
report={'status':'RUNNING','models':{},'captures':0,'rollbacks':0}
def run(cmd,w,label,ok=True):
 p=subprocess.run(list(map(str,cmd)),cwd=w,capture_output=True,text=True,timeout=float(os.environ.get('DSIM_TEST_COMMAND_TIMEOUT','180')))
 (w/(label+'.stdout')).write_text(p.stdout);(w/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==(0 if ok else 1),(label,p.returncode,p.stderr[-3000:]);return p

def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[i]) for key,(i,width,ranges) in declarations(meta).items()}
try:
 for name,wanted in EXPECTED.items():
  w=out/name;reference=None
  for backend,flags in [('serial',[]),('shared',['--shared-functions']),('wheel',['--shared-functions','--time-wheel'])]:
   run([compiler,w/'tb.sv',*flags,'--wave-support','--emit-cpp',w/(backend+'.cpp'),'-o',w/backend],w,backend+'-compile')
   p=run([w/backend,'--waveform',w/(backend+'.vcd'),'--wave-format','vcd','--wave-mode','ordered'],w,backend+'-run')
   assert p.stdout.splitlines()==wanted,(name,backend,p.stdout,wanted)
   current=stream(w/(backend+'.vcd'));report['captures']+=1
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete waveform')
  if name=='recursive_ref':
   code=(w/'shared.cpp').read_text();assert code.count('\ns.run();\n')==1
   (w/'replay.cpp').write_text(code.replace('\ns.run();\n','\ns.run_until(500);\nif(s.predict_until(2000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("unexpected commit");\nif(s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing rollback");\ns.run();\n'))
   strict=['-fp-model=strict'] if Path(config['DSIM_MODEL_CXX']).name in ('icpx','icpc') else []
   run([config['DSIM_MODEL_CXX'],'-std=c++17','-O2','-pthread',*strict,'-I'+config['DSIM_ZSTD_INCLUDE'],w/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',w/'replay'],w,'replay-compile')
   p=run([w/'replay','--waveform',w/'replay.vcd','--wave-format','vcd','--wave-mode','ordered'],w,'replay-run')
   assert p.stdout.splitlines()==wanted and stream(w/'replay.vcd')==reference
   report['captures']+=1;report['rollbacks']+=1
  report['models'][name]={'status':'PASS','trace':wanted,'source_sha256':hashlib.sha256((w/'tb.sv').read_bytes()).hexdigest()}
  print('PASS UVM values',name,flush=True)
 # Shared functions deliberately stay serial; protect all existing output files.
 w=out/'reject';w.mkdir(exist_ok=True);(w/'tb.sv').write_text('module top;endmodule\n');(w/'model.cpp').write_text('protected\n')
 p=run([compiler,'--shared-functions','--threads','2',w/'tb.sv','--emit-only','--emit-cpp',w/'model.cpp'],w,'parallel',False)
 assert '--shared-functions requires serial simulation' in p.stderr and (w/'model.cpp').read_text()=='protected\n'
 # Repeated call edges must share bodies and dependency metadata. Expanding
 # this diamond inline would require more than 2**25 copies of the leaf.
 w=out/'diamond';w.mkdir(exist_ok=True)
 functions=['function automatic int f0(int n);return 1;endfunction']
 for i in range(1,26):
  functions.append(f'function automatic int f{i}(int n);if(n==0)return {i};return f{i-1}(n-1)+f{i-1}(n-1);endfunction')
 (w/'tb.sv').write_text('module top;\n'+'\n'.join(functions)+'\nint result;initial begin result=f25(2);$display("TRACE diamond %0d",result);end\nendmodule\n')
 run([compiler,'--shared-functions',w/'tb.sv','--emit-cpp',w/'model.cpp','-o',w/'native'],w,'compile')
 assert run([w/'native'],w,'run').stdout.splitlines()==['TRACE diamond 92']
 size=(w/'model.cpp').stat().st_size;assert size<2_000_000,size
 report['diamond']={'status':'PASS','levels':26,'cpp_bytes':size,'source_sha256':hashlib.sha256((w/'tb.sv').read_bytes()).hexdigest()}
 # Preserve explicit diagnostics for unsupported recursive output arguments
 # and invalid class/type expressions rather than accepting incorrect values.
 negatives={
  'mixed_handle':'class C;endclass module top;C c;int n;initial c=1?c:n;endmodule',
  'type_value':'class A;typedef int value_type;endclass module top;int n;initial n=A::value_type;endmodule',
  'missing_required':'module top;function int f(int required);return required;endfunction int x;initial x=f();endmodule',
  'recursive_output':'module top;function automatic int f(int n,output int k);if(n==0)return 1;return f(n-1,k);endfunction int x,y;initial x=f(2,y);endmodule'}
 for name,source in negatives.items():
  w=out/('reject-'+name);w.mkdir(exist_ok=True);(w/'tb.sv').write_text(source);(w/'model.cpp').write_text('protected\n')
  run([compiler,'--shared-functions',w/'tb.sv','--emit-only','--emit-cpp',w/'model.cpp'],w,'compile',False)
  assert (w/'model.cpp').read_text()=='protected\n'
 report['negative_cases']=len(negatives)+1
 report['status']='PASS'
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
