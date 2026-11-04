"""SV specialized procedures: startup, feedback exclusions, NBA, domains and errors."""
from pathlib import Path
import json, subprocess, sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read, declarations
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
def run(cmd,work,label,success=True):
    p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=180)
    (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
    assert (p.returncode==0)==success,(label,p.stdout,p.stderr)
    return p.stdout
def streams(stream):
    meta,events=stream;values=[[] for _ in meta['signals']]
    for time,kind,payload in events:
        if kind=='value':values[payload[0]].append((time,payload[1]))
    return {name:(width,ranges,values[ident]) for name,(ident,width,ranges) in declarations(meta).items()}

captures=0
for name in ['design','parallel']:
    work=out/name;work.mkdir(exist_ok=True)
    source=ROOT/'tests/always_sv'/(name+'.sv');reference={};trace=None
    for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
        cpp=work/(backend+'.cpp');binary=work/backend
        run([compiler,source,'--wave-support',*flags,'--emit-cpp',cpp,'--emit-ir',work/(backend+'.json'),'-o',binary],work,backend+'-compile')
        current=run([binary],work,backend+'-none')
        if trace is None:trace=current
        assert current==trace
        if name=='design':
            lines=current.splitlines()
            assert lines[0]=='TRACE startup constant=a5 q=00',lines
            assert lines[1]=='TRACE held q=34 held=12 mixed=27 c=0 b=1 bits=00',lines
            assert lines[2].startswith('TRACE unknown held=x1z00110 mixed=xxxxxxxx wide=xz'),lines
            assert lines[3]=='TRACE final q=57 held=57 mixed=01 c=0 b=1 bits=11',lines
        for mode in ['ordered','settled']:
            for fmt in ['vcd','dwf']:
                dest=work/(backend+'-'+mode+'.'+fmt);dest.unlink(missing_ok=True)
                assert run([binary,'--waveform',dest,'--wave-format',fmt,'--wave-mode',mode],work,backend+'-'+mode+'-'+fmt)==trace
                stream=read(dest);captures+=1
                if backend=='serial' and fmt=='vcd':reference[mode]=stream
                assert streams(stream)==streams(reference[mode]),(name,backend,mode,fmt)
        if name=='parallel' and backend=='parallel':
            p=subprocess.run([str(binary),'--parallel-stats'],capture_output=True,text=True,check=True)
            assert '"partitions":2' in p.stderr,p.stderr
    # Exercise process PCs, implicit waits and pending NBAs across a rollback.
    code=(work/'serial.cpp').read_text()
    assert code.count('\ns.run();\n')==1
    replay=code.replace('\ns.run();\n','''
s.run_until(0);
if(s.predict_until(1000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("unexpected prediction commit");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing rollback");
s.run();
''')
    (work/'replay.cpp').write_text(replay)
    cache=(compiler.parent/'CMakeCache.txt').read_text().splitlines()
    config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache if '=' in x and not x.startswith('//')}
    run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
    dest=work/'replay.dwf';dest.unlink(missing_ok=True)
    assert run([work/'replay','--waveform',dest,'--wave-mode','ordered'],work,'replay-run')==trace
    assert streams(read(dest))==streams(reference['ordered']);captures+=1

negative={
    'comb-delay':'logic a;always_comb #1 a=0;',
    'latch-event':'logic a,b;always_latch @(a) b=a;',
    'ff-missing-event':'logic q;always_ff q<=0;',
    'ff-star':'logic a,q;always_ff @* q<=a;',
    'ff-nested':'logic clk,q;always_ff @(posedge clk) #1 q<=0;',
    'ff-extra-event':'logic clk,q;always_ff @(posedge clk) @(negedge clk) q<=0;',
    'comb-intra':'logic a;always_comb a=#1 0;',
    'ff-intra-nba':'logic clk,q;always_ff @(posedge clk) q<=#1 0;',
    'initial-writer':'logic a,q;initial q=0;always_comb q=a;',
    'declaration-writer':'logic q=0;always_comb q=1;',
    'overlapping-bits':'logic clk;logic[3:0] q;always_ff @(posedge clk) q[2:0]<=0;always_ff @(posedge clk) q[3:2]<=0;',
}
for name,body in negative.items():
    work=out/name;work.mkdir(exist_ok=True);(work/'top.sv').write_text('module top;\n'+body+'\nendmodule\n')
    run([compiler,work/'top.sv','--emit-only','--emit-cpp',work/'bad.cpp'],work,'reject',False)
    assert 'always_' in (work/'reject.stderr').read_text(),name
(out/'results.json').write_text(json.dumps(dict(status='PASS',captures=captures,negative_cases=len(negative),rollback=True),indent=2)+'\n')
print('PASS specialized always procedures',captures,'captures',len(negative),'rejections')
