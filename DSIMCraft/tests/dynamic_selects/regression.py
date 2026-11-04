"""Dynamic element packed selects, queue merging, captured targets and rollback."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/dynamic_selects'
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
native=json.loads((fixtures/'native-only/expected.json').read_text())
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
 checkpoint=1000 if name in ['arguments','control','timing'] else 0
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
  for port in ['a','b']:assert state[('top',port)][2][-1][1]==(0x63,0)
negative={
 'const':('logic[7:0] a[];task automatic t(const ref logic[7:0] x[]);x[0][1]=1;endtask initial begin a=new[1];t(a);end','cannot modify const ref'),
 'concat_net':('logic[7:0] a[];wire q;initial begin a=new[1];{a[0][2:0],q}=1;end','procedural assignment to a net'),
 'width':('logic[7:0] a[];integer k=2;initial begin a=new[1];a[0][0+:k]=1;end','indexed part-select width must be a positive constant'),
 'whole_nba':('logic[7:0] a[];initial a<=new[1];','blocking assignment without timing control'),
 'element_ref':('logic[7:0] a[];task automatic t(ref logic x);x=1;endtask initial begin a=new[1];t(a[0][0]);end','ref does not support packed bit/part selections'),
}
for name,(body,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module top;'+body+' endmodule\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
 run([compiler,path,'--emit-only','--emit-cpp',dest],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text())
 assert not dest.exists(),(name,'partial output')
report=dict(status='PASS',shared_models=len(expected),native_models=len(native),captures=captures,failed_predictions=predictions,negative_cases=len(negative),real_parallel_partitions=2)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS dynamic selects:',captures,'captures,',predictions,'failed predictions, partial NBA merges and two partitions')
