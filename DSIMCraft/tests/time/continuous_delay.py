"""Compile delayed continuous assignments; compare complete waves and replay."""
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_waveforms import compare
from continuous_delay_cases import CASES,IEEE_CASES

compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
def run(args,work,label,success=True):
    result=subprocess.run(list(map(str,args)),cwd=work,text=True,capture_output=True,timeout=180)
    (work/(label+'.stdout')).write_text(result.stdout);(work/(label+'.stderr')).write_text(result.stderr)
    assert (result.returncode==0)==success,(label,result.stdout,result.stderr)
    return result.stdout+result.stderr

config={line.split('=',1)[0].split(':',1)[0]:line.split('=',1)[1] for line in (compiler.parent/'CMakeCache.txt').read_text().splitlines() if '=' in line and not line.startswith('//')}
captures=0;report=dict(status='RUNNING',cases={},generated_replay=False)
for name,(source,expected) in CASES.items():
    work=out/name;work.mkdir(exist_ok=True);(work/'top.v').write_text(source)
    run([compiler,work/'top.v','--wave-support','--emit-ir',work/'ir.json','--emit-cpp',work/'model.cpp','-o',work/'native'],work,'compile')
    code=(work/'model.cpp').read_text();assert '#define DSIM_CONTINUOUS_DELAY_ENABLED 1' in code
    assert json.loads((work/'ir.json').read_text())['continuous_delay_mode']=='vcs'
    assert '#define DSIM_CONTINUOUS_DELAY_IEEE_MODE 1' not in code
    text=run([work/'native'],work,'native-none');assert text.splitlines()==expected,(name,text,expected)
    variants=['native']
    if name=='parts':
        assert code.count('\ns.run();\n')==1
        control='''
s.run_until(3500);
bool accepted=s.predict_until(8000,[](Sim& probe) {
 for(size_t id=0;id<probe.signals.size();++id) {
  const auto& sig=probe.signals[id];if(!sig.net)probe.set(int(id),V::x(sig.value.w));
 }
},[](const Sim&){return false;},[](Sim&){});
if(accepted||s.prediction_stats.rollbacks!=1)throw std::runtime_error("continuous delay replay failed");
s.run();
'''
        (work/'replay.cpp').write_text(code.replace('\ns.run();\n',control))
        (work/'boundary.cpp').write_text(code.replace('\ns.run();\n','\ns.run_until(3500);s.run_until(8000);s.run();\n'))
        for variant in ['boundary','replay']:
            run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/(variant+'.cpp'),config['DSIM_ZSTD_LIBRARY'],'-o',work/variant],work,variant+'-compile')
        variants+=['boundary','replay'];report['generated_replay']=True
    for mode in ['ordered','settled']:
        paths={}
        for variant in variants:
            paths[variant]=[]
            for codec,fmt in [('vcd','vcd'),('raw','dwf'),('zstd','dwf')]:
                label=variant+'-'+mode+'-'+codec;dest=work/(label+'.'+fmt);dest.unlink(missing_ok=True)
                args=[work/variant,'--waveform',dest,'--wave-format',fmt,'--wave-mode',mode,'--wave-block-events','7']
                if fmt=='dwf':args+=['--wave-codec',codec]
                text=run(args,work,label);assert text.splitlines()==expected,(name,label,text,expected)
                paths[variant].append(dest);captures+=1
            for dest in paths[variant][1:]:compare(paths[variant][0],dest)
        if 'replay' in variants:compare(paths['boundary'][0],paths['replay'][0])
    report['cases'][name]=dict(status='PASS',expected=expected)

ieee={}
for name,(source,expected) in IEEE_CASES.items():
    work=out/('ieee-'+name);work.mkdir(exist_ok=True);(work/'top.v').write_text(source)
    run([compiler,work/'top.v','--continuous-delay-mode','ieee','--emit-ir',work/'ir.json',
         '--emit-cpp',work/'model.cpp','-o',work/'native'],work,'compile')
    assert json.loads((work/'ir.json').read_text())['continuous_delay_mode']=='ieee'
    assert '#define DSIM_CONTINUOUS_DELAY_IEEE_MODE 1' in (work/'model.cpp').read_text()
    assert run([work/'native'],work,'native-none').splitlines()==expected
    ieee[name]=dict(status='PASS',expected=expected)
for arguments in [[],['bad'],['vcs','--continuous-delay-mode','ieee'],['vcs','-E']]:
    result=subprocess.run([str(compiler),'--continuous-delay-mode',*arguments],text=True,capture_output=True)
    assert result.returncode and '--continuous-delay-mode' in result.stderr

rejected={
 'dynamic':'reg d=0;wire q;assign #(d) q=d;',
 'negative':'reg d=0;wire q;assign #(-1) q=d;',
 'net-delay':'wire #3 q;assign q=1;',
 'four-delays':'wire q;assign #(1,2,3,4) q=1;',
 'weak':'wire q;assign (weak1,weak0) #3 q=1;',
 'gate-third':'reg d=0;wire q;and #(1,2,3) g(q,d,d);',
 'unknown-delay':"wire q;assign #(1'bx) q=1;",
 'overflow-delay':'wire q;assign #18446744073709551616 q=1;',
}
for name,body in rejected.items():
    work=out/('reject-'+name);work.mkdir(exist_ok=True)
    (work/'top.v').write_text('module top;'+body+'endmodule\n')
    text=run([compiler,work/'top.v','--emit-only','--emit-cpp',work/'model.cpp'],work,'compile',False)
    assert 'dsim:' in text and not (work/'model.cpp').exists()
report.update(status='PASS',native_captures=captures,strict_rejections=list(rejected),ieee_cases=ieee)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS continuous/primitive delays: '+str(len(CASES))+' cases, native codecs, actual generated pending-event replay and strict diagnostics')
