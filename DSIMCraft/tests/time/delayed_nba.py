"""Run delayed NBA RTL, codecs and an actual generated checkpoint replay."""
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read
from delayed_nba_cases import CASES

compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
def run(args,work,label,success=True):
    result=subprocess.run(list(map(str,args)),cwd=work,text=True,capture_output=True,timeout=180)
    (work/(label+'.stdout')).write_text(result.stdout);(work/(label+'.stderr')).write_text(result.stderr)
    assert (result.returncode==0)==success,(label,result.stdout,result.stderr)
    return result.stdout+result.stderr

cache=(compiler.parent/'CMakeCache.txt').read_text().splitlines()
config={line.split('=',1)[0].split(':',1)[0]:line.split('=',1)[1] for line in cache if '=' in line and not line.startswith('//')}
captures=0;report=dict(status='RUNNING',cases={},generated_replay=False)
for name,(source,expected) in CASES.items():
    work=out/name;work.mkdir(exist_ok=True);(work/'top.v').write_text(source)
    run([compiler,work/'top.v','--wave-support','--emit-cpp',work/'model.cpp','-o',work/'native'],work,'compile')
    code=(work/'model.cpp').read_text();assert '#define DSIM_DELAYED_NBA_ENABLED 1' in code
    text=run([work/'native'],work,'native-none');assert text.splitlines()==expected,(name,text,expected)
    variants=['native']
    if name=='transport':
        assert code.count('\ns.run();\n')==1
        control='''
s.run_until(500);
bool accepted=s.predict_until(6500,[](Sim& probe) {
 for(size_t id=0;id<probe.signals.size();++id) {
  const auto& sig=probe.signals[id];if(!sig.net)probe.set(int(id),V::x(sig.value.w));
 }
},[](const Sim&){return false;},[](Sim&){});
if(accepted||s.prediction_stats.rollbacks!=1)throw std::runtime_error("delayed NBA replay failed");
s.run();
'''
        (work/'replay.cpp').write_text(code.replace('\ns.run();\n',control))
        (work/'boundary.cpp').write_text(code.replace('\ns.run();\n','\ns.run_until(500);s.run_until(6500);s.run();\n'))
        for variant in ['boundary','replay']:
            run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/(variant+'.cpp'),config['DSIM_ZSTD_LIBRARY'],'-o',work/variant],work,variant+'-compile')
        variants+=['boundary','replay'];report['generated_replay']=True
    for mode in ['ordered','settled']:
        streams={}
        for variant in variants:
            streams[variant]=[]
            for codec,fmt in [('vcd','vcd'),('raw','dwf'),('zstd','dwf')]:
                label=variant+'-'+mode+'-'+codec;dest=work/(label+'.'+fmt);dest.unlink(missing_ok=True)
                args=[work/variant,'--waveform',dest,'--wave-format',fmt,'--wave-mode',mode,'--wave-block-events','7']
                if fmt=='dwf':args+=['--wave-codec',codec]
                text=run(args,work,label);assert text.splitlines()==expected,(name,label,text,expected)
                streams[variant].append(read(dest));captures+=1
            assert all(stream==streams[variant][0] for stream in streams[variant]),(name,mode,variant)
        if 'replay' in variants:
            assert streams['boundary'][0]==streams['replay'][0],(name,mode,'boundary/replay')
    report['cases'][name]=dict(status='PASS',expected=expected)
for name,control in [('event','@*'),('negative','#(-1)')]:
    work=out/('reject-'+name);work.mkdir(exist_ok=True)
    (work/'model.cpp').unlink(missing_ok=True)
    (work/'top.v').write_text('module top;reg d,q;initial q <= '+control+' d;endmodule\n')
    text=run([compiler,work/'top.v','--emit-only','--emit-cpp',work/'model.cpp'],work,'compile',False)
    assert 'dsim:' in text and not (work/'model.cpp').exists()
report.update(status='PASS',native_captures=captures)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS delayed NBA RTL: nine cases, native codecs, actual generated pending-event replay and strict controls')
