"""Module and primitive instance arrays: ports, state, timing and replay."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=Path(__file__).resolve().parent;expected=json.loads((fixtures/'expected.json').read_text())
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in (compiler.parent/'CMakeCache.txt').read_text().splitlines() if '=' in x and not x.startswith('//')}
def run(command,work,label,ok=True):
 p=subprocess.run(list(map(str,command)),cwd=work,text=True,capture_output=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode>=0 and (p.returncode==0)==ok,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout
def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
report={'status':'RUNNING','models':{},'captures':0,'rollbacks':0}
for name,wanted in expected.items():
 work=out/name;work.mkdir(exist_ok=True);references={}
 source=fixtures/(name+'.sv')
 language=[]
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,source,*language,*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-compile')
  trace=run([work/backend],work,backend+'-run');assert [line for line in trace.splitlines() if line.startswith('TRACE')]==wanted,(name,backend,trace,wanted)
  for mode in ['ordered','settled']:
   for fmt in ['vcd','dwf']:
    wave=work/(backend+'-'+mode+'.'+fmt)
    wave.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',wave,'--wave-mode',mode,'--wave-format',fmt],work,backend+'-'+mode+'-'+fmt)==trace
    state=streams(wave);report['captures']+=1
    if backend=='serial' and fmt=='vcd':references[mode]=state
    assert state==references[mode],(name,backend,mode,fmt)
  if backend=='parallel' and name=='parallel':
   run([work/backend,'--parallel-stats'],work,'parallel-stats')
   assert '"partitions":2' in (work/'parallel-stats.stderr').read_text()
 if name=='parallel':
  state=timeline(*read(work/'serial-settled.vcd'))
  for port in ['one','two']:assert state[('top',port)][2][-1][1]==(0x7303,0)
 if name in ['state','primitives','generated']:
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
s.run_until(1000);
if(s.predict_until(30000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
  run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  (work/'replay.dwf').unlink(missing_ok=True)
  assert run([work/'replay','--waveform',work/'replay.dwf','--wave-mode','ordered'],work,'replay-run')==(work/'serial-run.stdout').read_text()
  assert streams(work/'replay.dwf')==references['ordered'];report['rollbacks']+=1;report['captures']+=1
 report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'trace':wanted}
 print('PASS instance arrays',name,flush=True)

negative={
 'width':('module leaf(input[3:0] a);endmodule module top;logic[4:0] a;leaf u[2:0](a);endmodule','instance array connection width'),
 'primitive_width':('module top;wire q;logic[2:0] a;buf u[1:0](q,a);endmodule','instance array connection width'),
 'runtime_bound':('module leaf;endmodule module top;integer n;leaf u[n:0]();endmodule','instance array bounds must be constant'),
 'unknown_bound':("module leaf;endmodule module top;leaf u[1'bx:0]();endmodule",'instance array bound is unknown'),
 'oversize':('module leaf;endmodule module top;leaf u[65536:0]();endmodule','instance array exceeds 65536'),
 'wide_bound':("module leaf;endmodule module top;leaf u[64'h100000001:0]();endmodule",'instance array bound exceeds'),
 'unsigned_bound':("module leaf;endmodule module top;leaf u[32'h80000000:0]();endmodule",'instance array bound exceeds'),
 'unpacked_port':('module leaf(input integer a[0:1]);endmodule module top;integer a[0:1];leaf u[1:0](a);endmodule','unpacked ports in module instance arrays'),
 'dynamic_output':('module leaf(output wire q);assign q=0;endmodule module top;logic[3:0] q;integer i;leaf u[1:0](q[i]);endmodule','variable selects in output/inout'),
 'side_effect':('module leaf(input[3:0] a);endmodule module top;integer calls=0;function automatic logic[3:0] value();calls++;return calls;endfunction leaf u[1:0](value());endmodule','instance array port expressions must have no persistent side effects'),
 'variable_broadcast':('module leaf(output logic q);initial q=0;endmodule module top;logic q;leaf u[1:0](q);endmodule','variable port driver conflicts'),
}

for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text(source+'\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
 run([compiler,path,'--emit-only','--emit-cpp',dest],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text())
 assert not dest.exists(),name
# No runtime state is shared by the two independent array members.
parallel_ir=json.loads((out/'parallel/parallel.json').read_text())
assert parallel_ir['parallel']['partitions']==2
assert {x['scope'] for x in parallel_ir['ports']}=={'top.u[1]','top.u[0]'}
report.update(status='PASS',negative_cases=len(negative),real_parallel_partitions=2)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS instance arrays compatibility',report['captures'],'captures and',report['rollbacks'],'rollbacks')
