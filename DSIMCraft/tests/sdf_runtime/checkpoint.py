"""Replay real generated path state with pending timers and wrong input history."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read
compiler=Path(sys.argv[1]).resolve();base=Path(sys.argv[2]).resolve()
cache=(compiler.parent/'CMakeCache.txt').read_text().splitlines();config={line.split('=',1)[0].split(':',1)[0]:line.split('=',1)[1] for line in cache if '=' in line and not line.startswith('//')}
for name in (sys.argv[3:] or ['latest','multiple','ff']):
 w=base/name
 def run(cmd,log):
  p=subprocess.run(list(map(str,cmd)),cwd=w,text=True,capture_output=True,timeout=180);(w/log).write_text(p.stdout+p.stderr)
  assert p.returncode==0,(name,cmd,p.stdout,p.stderr);assert 'runtime error:' not in p.stderr
  return p.stdout
 code=(w/'native.dsim.cpp').read_text();assert code.count('\ns.run();\n')==1
 replay='''
 s.run_until(101);
 auto rolled=s.predict_until(125,[](Sim& probe) {
   for(size_t id=0;id<probe.signals.size();++id){const auto& sig=probe.signals[id];if(!sig.net)probe.set(int(id),V(0,0,sig.value.w));}
   probe.run_until(102);
   for(size_t id=0;id<probe.signals.size();++id){const auto& sig=probe.signals[id];if(!sig.net)probe.set(int(id),V(mask(sig.value.w),0,sig.value.w));}
 },[](const Sim&){return false;},[](Sim&){});
 if(rolled||s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing path rollback");
 auto accepted=s.predict_until(150,[](Sim&){},[](const Sim&){return true;},[](Sim&){});
 if(!accepted)throw std::runtime_error("missing path commit");
 s.run();
'''
 (w/'boundary.cpp').write_text(code.replace('\ns.run();\n','\ns.run_until(101);s.run_until(125);s.run_until(150);s.run();\n'))
 (w/'replay.cpp').write_text(code.replace('\ns.run();\n',replay))
 cmd=['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],w/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',w/'replay']
 run(cmd,'replay-compile.log')
 run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],w/'boundary.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',w/'boundary'],'boundary-compile.log')
 for mode in ['ordered','settled']:
  results=[];waves=[]
  for variant in ['boundary','replay']:
   dest=w/f'{variant}-{mode}.dwf';dest.unlink(missing_ok=True)
   results.append(run([w/variant,'--waveform',dest,'--wave-mode',mode,'--wave-block-events','7'],f'{variant}-{mode}.log'));waves.append(read(dest))
  assert results[0]==results[1],(name,mode,'stdout');assert waves[0]==waves[1],(name,mode,'waveform')
 print('PASS generated SDF checkpoint',name,flush=True)
