#!/usr/bin/env python3
"""Exercise actual generated RTL state machines and Liberty state restoration."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read

def main():
    ap=argparse.ArgumentParser();ap.add_argument('compiler',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args()
    compiler=a.compiler.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    # Large enough temporal span to checkpoint active Liberty storage. Alias and
    # NBA cases additionally test restored net-driver and process closure state.
    cases=['rtl_states','gate-seq_feedback','gate-seq_latches','gate-wide_atomic']
    import importlib.util
    spec=importlib.util.spec_from_file_location('gate',ROOT/'tests/gate/regression.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
    from cases import CASES
    for name in cases:
        w=out/name;w.mkdir(exist_ok=True)
        def run(args,log):
            p=subprocess.run(list(map(str,args)),cwd=w,text=True,capture_output=True,timeout=180)
            (w/log).write_text(p.stdout+p.stderr);assert p.returncode==0,(name,args,p.stdout,p.stderr)
            return p.stdout
        if name.startswith('gate-'):args=g.command(compiler,name[5:])
        else:
            (w/'top.v').write_text(CASES[name]);args=[compiler,w/'top.v']
        run([*args,'--wave-support','--emit-cpp',w/'model.cpp','-o',w/'baseline'],'compile.log')
        code=(w/'model.cpp').read_text();assert code.count('\ns.run();\n')==1
        # A deliberately wrong branch runs beyond a mid-simulation checkpoint.
        # It must disappear from stdout and from ordered waveforms completely.
        control='''
 s.run_until(1);
 if(!s.finished) {
  bool accepted=s.predict_until(100000,[](Sim& probe) {
   for(size_t id=0;id<probe.signals.size();++id) {
    auto& sig=probe.signals[id];
    if(!sig.net)probe.set(int(id),V(0xa5,0,sig.value.w));
   }
  },[](const Sim&) {return false;},[](Sim&) {});
  if(accepted||s.prediction_stats.rollbacks!=1)throw std::runtime_error("prediction failed to roll back");
 }
 s.run();
'''
        (w/'replay.cpp').write_text(code.replace('\ns.run();\n',control))
        cache=(compiler.parent/'CMakeCache.txt').read_text().splitlines();config={line.split('=',1)[0].split(':',1)[0]:line.split('=',1)[1] for line in cache if '=' in line and not line.startswith('//')}
        run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],w/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',w/'replay'],'replay-compile.log')
        for mode in ['ordered','settled']:
            results=[];waves=[]
            for variant in ['baseline','replay']:
                dest=w/f'{variant}-{mode}.dwf';dest.unlink(missing_ok=True)
                results.append(run([w/variant,'--waveform',dest,'--wave-mode',mode,'--wave-block-events','7'],f'{variant}-{mode}.log'))
                waves.append(read(dest))
            assert results[0]==results[1],(name,mode,results)
            assert waves[0]==waves[1],(name,mode)
        print('PASS generated checkpoint and rollback',name,flush=True)
if __name__=='__main__':main()
