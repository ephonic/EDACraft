"""Native bind/final: complete streams, real partitions, finish fences, rollback."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations,timeline

def run(command,work,label):
 p=subprocess.run(list(map(str,command)),cwd=work,capture_output=True,text=True,timeout=240)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout

def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
expected=json.loads((fixtures/'expected.json').read_text());report={'status':'RUNNING','models':{},'captures':0,'rollbacks':0,'real_parallel_models':[]}
try:
 for name,wanted in expected.items():
  work=out/name;work.mkdir(exist_ok=True);reference={};wave_enabled=name!='empty'
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,fixtures/(name+'.sv'),*flags,*(['--wave-support'] if wave_enabled else []),'--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-compile')
   for mode in (['ordered','settled'] if wave_enabled else ['plain']):
    wave=work/(backend+'-'+mode+'.vcd');wave.unlink(missing_ok=True)
    text=run([work/backend,*(['--waveform',wave,'--wave-format','vcd','--wave-mode',mode] if wave_enabled else [])],work,backend+'-'+mode)
    assert text.splitlines()==wanted,(name,backend,mode,text,wanted)
    if wave_enabled:
     current=stream(wave)
     if backend=='serial':reference[mode]=current
     else:assert current==reference[mode],(name,backend,mode,'complete stream',[(k,current[k],reference[mode].get(k)) for k in current if current[k]!=reference[mode].get(k)])
     report['captures']+=1
  if name.startswith('partitioned'):
   ir=json.loads((work/'parallel.json').read_text());assert ir['parallel']['partitions']==2,ir['parallel'];report['real_parallel_models'].append(name)
   wave=timeline(*read(work/'parallel-settled.vcd'));tick=1000 if name.endswith('early') else 3000
   for lane,value in [('u',11 if name.endswith('early') else 12),('v',12 if name.endswith('early') else 13)]:
    assert wave[('top',lane,'result')][2][-1]==(tick,(value,0)),(name,lane,wave[('top',lane,'result')])
  # A rejected prediction reaches finalization, discards output/waves/state,
  # then replays. A repeated run must never execute finals again.
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
if(s.predict_until(10000,[](Sim& simulated){simulated.run();},[](const Sim&){return false;},[](Sim& corrected){corrected.run();}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();s.run();
'''))
  run(['c++','-std=c++17','-O2','-pthread','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',*([config['DSIM_ZSTD_LIBRARY']] if wave_enabled else []),'-o',work/'replay'],work,'replay-compile')
  wave=work/'replay.vcd';wave.unlink(missing_ok=True)
  assert run([work/'replay',*(['--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'] if wave_enabled else [])],work,'replay-run').splitlines()==wanted,(name,'replay output')
  if wave_enabled:assert stream(wave)==reference['ordered'],(name,'replay stream');report['captures']+=1
  report['rollbacks']+=1
  report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),'output':wanted}
  print('PASS final_bind',name,flush=True)
 negatives={
  'delay':('module top;final #1 $display("bad");endmodule','scheduling controls'),
  'intra_delay':('module top;int a;final a=#1 2;endmodule','scheduling controls'),
  'nba':('module top;int a;final a<=2;endmodule','scheduling controls'),
  'wait':('module top;int a;final wait(a);endmodule','scheduling controls'),
  'fork':('module top;final fork $display("bad");join endmodule','scheduling controls'),
  'task':('module top;task t;begin end endtask final t();endmodule','without task calls'),
  'finish_argument':('module top;final $finish(3);endmodule','argument must be 0, 1 or 2'),
  'bad_target':('module top;endmodule module observer;endmodule bind absent observer o();','declared module type'),
  'duplicate':('module lane;endmodule module observer;endmodule bind lane observer o(); bind lane observer o(); module top;lane u();endmodule','redefined'),
 }
 for name,(body,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text(body+'\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  p=subprocess.run([str(compiler),str(source),'--emit-only','--emit-cpp',str(dest)],capture_output=True,text=True)
  (out/(name+'.stderr')).write_text(p.stderr)
  assert p.returncode==1 and diagnostic in p.stderr and not dest.exists(),(name,p.returncode,p.stdout,p.stderr)
 run(['c++','-std=c++17','-O2','-pthread','-I'+str(ROOT/'include'),fixtures/'kernel.cpp','-o',out/'kernel'],out,'kernel-compile')
 run([out/'kernel'],out,'kernel-run')
 report.update(status='PASS',negative_cases=len(negatives),coordinator_kernel='PASS')
except Exception as error:report.update(status='FAIL',error=str(error));raise
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS final_bind:',len(report['models']),'models,',report['captures'],'captures,',report['rollbacks'],'rollbacks')
