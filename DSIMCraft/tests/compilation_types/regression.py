"""Execute compilation-unit types with waveform/checkpoint equivalence."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tests/waveform'))
from reader import read,declarations,timeline
compiler,out=map(lambda p:Path(p).resolve(),sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]) if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={s.split('=',1)[0].split(':',1)[0]:s.split('=',1)[1] for s in cache.read_text().splitlines() if '=' in s and not s.startswith('//')}
fixtures=root/'tests/compilation_types';expected=json.loads((fixtures/'expected.json').read_text())
report=dict(status='RUNNING',models={},captures=0,rollbacks=0,commits=0)
def run(args,work,label,ok=True):
 p=subprocess.run(list(map(str,args)),cwd=work,text=True,capture_output=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode>=0 and (p.returncode==0)==ok,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout
def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
for arg in sys.argv[4:]:
 if arg.startswith('--model='):expected={arg.split('=',1)[1]:expected[arg.split('=',1)[1]]}
for name,wanted in expected.items():
 work=out/name;work.mkdir(exist_ok=True);reference={}
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,fixtures/(name+'.sv'),*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-compile')
  assert run([work/backend],work,backend+'-run').splitlines()==wanted,(name,backend)
  for mode in ['ordered','settled']:
   for fmt,extra in [('vcd',[]),('dwf',[]),('async.dwf',['--wave-async','--wave-buffer-bytes','4096'])]:
    path=work/(backend+'-'+mode+'.'+fmt);path.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',path,'--wave-format','vcd' if fmt=='vcd' else 'dwf','--wave-mode',mode,*extra],work,backend+'-'+mode+'-'+fmt).splitlines()==wanted
    state=streams(path);report['captures']+=1
    if backend=='serial' and fmt=='vcd':reference[mode]=state
    assert state==reference[mode],(name,backend,mode,fmt)
    if fmt=='async.dwf':assert path.read_bytes()==(work/(backend+'-'+mode+'.dwf')).read_bytes()
 if name=='parallel':
  ir=json.loads((work/'parallel.json').read_text())
  assert ir['parallel']['partitions']==2,ir['parallel']
  lanes=timeline(*read(work/'parallel-ordered.async.dwf'))
  for signal,value in [('one',4),('two',12)]:assert lanes[('top',signal)][2][-1][1]==(value,0)
  report['real_parallel_partitions']=2
 if name=='rollback':
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
s.run_until(1);
if(s.predict_until(4,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("unexpected commit");
if(!s.predict_until(4,[](Sim&){},[](const Sim&){return true;},[](Sim&){}))throw std::runtime_error("missing commit");
if(s.prediction_stats.rollbacks!=1||s.prediction_stats.commits!=1)throw std::runtime_error("prediction accounting");
s.run();
'''))
  run([config['DSIM_MODEL_CXX'],'-std=c++17','-O2','-pthread','-I'+str(root/'include'),'-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-I'+config['DSIM_Z3_INCLUDE'],config['DSIM_Z3_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  path=work/'replay.dwf';path.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',path,'--wave-mode','ordered','--wave-async'],work,'replay-run').splitlines()==wanted
  assert streams(path)==reference['ordered'];report['captures']+=1;report['rollbacks']+=1;report['commits']+=1
  path=work/'selected.dwf';path.unlink(missing_ok=True)
  run([work/'replay','--waveform',path,'--wave-async','--wave-scope','top','--wave-include','*observed','--wave-start','2','--wave-end','3'],work,'selected-run')
  lanes=timeline(*read(path));assert set(lanes)=={('top','observed')}
  assert lanes[('top','observed')][2]==[(2,(3,0)),(3,(9,0))],lanes
  report['captures']+=1
 report['models'][name]={'status':'PASS','backend_requests':3,'source_sha256':hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest()}
 (out/'results.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS compilation types',name,flush=True)
negative=json.loads((fixtures/'negative.json').read_text())
for name,body in negative.items():
 work=out/name;work.mkdir(exist_ok=True);source=work/'bad.sv';source.write_text(body+'\n')
 cpp=work/'bad.cpp';cpp.unlink(missing_ok=True)
 run([compiler,source,'--emit-only','--emit-cpp',cpp],work,'reject',False);assert not cpp.exists()
if not any(arg.startswith('--model=') for arg in sys.argv[4:]):
 work=out/'source-order';work.mkdir(exist_ok=True)
 first=work/'types.sv';second=work/'main.sv'
 first.write_text('typedef bit[4:0] Word;class C;static int count=0;Word x=8;function new();count++;endfunction endclass\n')
 second.write_text('module top;C value;initial begin value=new;if(value.x!=8||C::count!=1)$fatal(1,"file type identity");$display("TRACE unit files %0d %0d",value.x,C::count);end endmodule\n')
 filelist=work/'files.f';filelist.write_text(str(first)+'\n'+str(second)+'\n')
 included=work/'included.sv';included.write_text('`include "types.sv"\n'+second.read_text())
 for label,arguments in [('direct',[first,second]),('filelist',['-f',filelist]),('include',[included])]:
  exe=work/label
  run([compiler,*arguments,'-o',exe],work,label+'-compile')
  assert run([exe],work,label+'-run').splitlines()==['TRACE unit files 8 1']
 cpp=work/'reversed.cpp';cpp.unlink(missing_ok=True)
 run([compiler,second,first,'--emit-only','--emit-cpp',cpp],work,'reverse-reject',False)
 assert not cpp.exists()
 report.update(source_order_runs=3,reversed_source_rejections=1)
 work=out/'generic'
 for length in [1,149]:
  alias=out/('compiler-'+('x'*length));alias.unlink(missing_ok=True);alias.symlink_to(compiler)
  cpp=work/('repeat-'+str(length)+'.cpp')
  run([alias,fixtures/'generic.sv','--wave-support','--emit-only','--emit-cpp',cpp],work,'repeat-'+str(length))
  assert cpp.read_bytes()==(work/'serial.cpp').read_bytes()
 report['repeatable_emission_entry_paths']=2
report.update(status='PASS',negative_cases=len(negative))
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
