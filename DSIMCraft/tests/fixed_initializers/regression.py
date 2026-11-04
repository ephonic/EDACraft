"""Fixed array declaration copies, entry lifetime and rollback."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/fixed_initializers'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in (compiler.parent/'CMakeCache.txt').read_text().splitlines() if '=' in x and not x.startswith('//')}
def run(cmd,work,label,ok=True):
 p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode>=0,(label,'process crashed',p.returncode,p.stderr)
 assert (p.returncode==0)==ok,(label,p.stdout,p.stderr)
 return p.stdout
def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
expected=json.loads((fixtures/'expected.json').read_text())
native={}
captures=0;predictions=0
for name,wanted in {**expected,**native}.items():
 work=out/name;work.mkdir(exist_ok=True);references={}
 source=fixtures/('native-only' if name in native else '')/(name+'.sv')
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,source,'--wave-support',*flags,'--emit-ir',work/(backend+'.json'),'--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
  trace=run([work/backend],work,backend+'-run');assert [x for x in trace.splitlines() if x.startswith('TRACE')]==wanted,(name,backend,trace)
  for mode in ['ordered','settled']:
   for fmt in ['vcd','dwf']:
    dest=work/(backend+'-'+mode+'.'+fmt);dest.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',dest,'--wave-mode',mode,'--wave-format',fmt],work,backend+'-'+mode+'-'+fmt)==trace
    state=streams(dest);captures+=1
    assert all('$activation' not in '.'.join(key) for key in state),(name,'automatic state exported')
    if backend=='serial' and fmt=='vcd':references[mode]=state
    assert state==references[mode],(name,backend,mode,fmt)
  if backend=='parallel' and name=='parallel':
   run([work/backend,'--parallel-stats'],work,'stats')
   assert '"partitions":2' in (work/'stats.stderr').read_text()
 checkpoint=1000 if name in ['automatic','control','views'] else 0
 code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
 (work/'replay.cpp').write_text(code.replace('\ns.run();\n',f'''
s.run_until({checkpoint});
if(s.predict_until(30000,[](Sim&){{}},[](const Sim&){{return false;}},[](Sim&){{}}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
 run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
 dest=work/'replay.dwf';dest.unlink(missing_ok=True)
 assert run([work/'replay','--waveform',dest,'--wave-mode','ordered'],work,'replay-run')==(work/'serial-run.stdout').read_text()
 assert streams(dest)==references['ordered'];captures+=1;predictions+=1
 # Final observations independently test values rather than just backend agreement.
 if name=='parallel':
  state=timeline(*read(work/'serial-settled.vcd'))
  for port in ['one','two']:assert state[('top',port)][2][-1][1]==(0x8602,0)
negative={
 'width':('logic[7:0] a[2];logic[15:0] b[2]=a;initial begin end','compatible element types'),
 'signed':('logic signed[7:0] a[2];logic[7:0] b[2]=a;initial begin end','compatible element types'),
 'atomic':('integer a[2];int b[2]=a;initial begin end','compatible element types'),
 'atomic_assignment':('integer a[2];int b[2];initial b=a;','compatible element types'),
 'rank':('integer a[2][2];integer b[4]=a;initial begin end','rank mismatch'),
 'size':('integer a[3];integer b[2]=a;initial begin end','dimension size mismatch'),
 'static_auto':('task automatic work(input integer x[2]);static integer a[2]=x;begin end endtask integer a[2];initial work(a);','static fixed array initializer cannot reference an automatic variable'),
 'new_fixed':('integer a[2]=new[2];initial begin end','new requires a dynamic array declaration'),
 'net':('wire[7:0] a[2];wire[7:0] b[2]=a;initial begin end','net array declaration initializers'),
}

for name,(body,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module top;'+body+' endmodule\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
 run([compiler,path,'--emit-only','--emit-cpp',dest],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text())
 assert not dest.exists(),(name,'partial output')
report=dict(status='PASS',shared_models=len(expected),native_models=len(native),captures=captures,failed_predictions=predictions,negative_cases=len(negative),real_parallel_partitions=2)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS fixed initializers:',captures,'captures,',predictions,'failed predictions and two partitions')
