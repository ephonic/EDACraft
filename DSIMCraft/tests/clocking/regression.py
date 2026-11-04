"""Clocking regions, instance identity, waveform equivalence and saved state."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'tests/waveform'))
from reader import read,declarations
compiler,out=map(lambda s:Path(s).resolve(),sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]) if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={s.split('=',1)[0].split(':',1)[0]:s.split('=',1)[1] for s in cache.read_text().splitlines() if '=' in s and not s.startswith('//')}
report=dict(status='RUNNING',models={},captures=0,rollbacks=0,commits=0,negative_cases=0,budget_resumes=0)
def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
def run(args,work,label,ok=True):
    p=subprocess.run(list(map(str,args)),cwd=work,capture_output=True,text=True,timeout=240)
    (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
    assert p.returncode==(0 if ok else 1),(label,p.returncode,p.stdout,p.stderr)
    return p.stdout
def stream(path):
    meta,events=read(path);values=[[] for _ in meta['signals']]
    for time,kind,value in events:
        if kind=='value':values[value[0]].append((time,value[1]))
    return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
def native(source,exe,work,label,extra=()):
    strict=['-fp-model=strict'] if Path(config['DSIM_MODEL_CXX']).name in ('icpx','icpc') else []
    run([config['DSIM_MODEL_CXX'],'-std=c++17','-O2','-pthread',*strict,*extra,'-I'+str(root/'include'),'-I'+config['DSIM_ZSTD_INCLUDE'],source,config['DSIM_ZSTD_LIBRARY'],'-o',exe],work,label)
expected=json.loads((fixtures/'expected.json').read_text())
for option in sys.argv[4:]:
    if option.startswith('--model='):expected={option.split('=',1)[1]:expected[option.split('=',1)[1]]}
for name,wanted in expected.items():
    work=out/name;work.mkdir(exist_ok=True);reference={}
    for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
        run([compiler,fixtures/(name+'.sv'),*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-compile')
        assert run([work/backend],work,backend+'-run').splitlines()==wanted,(name,backend)
        for mode in ('ordered','settled'):
            for suffix,extra in [('vcd',[]),('dwf',[]),('async.dwf',['--wave-async','--wave-buffer-bytes','4096'])]:
                wave=work/(backend+'-'+mode+'.'+suffix);wave.unlink(missing_ok=True)
                text=run([work/backend,'--waveform',wave,'--wave-format','vcd' if suffix=='vcd' else 'dwf','--wave-mode',mode,*extra],work,backend+'-'+mode+'-'+suffix)
                assert text.splitlines()==wanted
                current=stream(wave)
                if backend=='serial' and suffix=='vcd':reference[mode]=current
                assert current==reference[mode],(name,backend,mode,suffix)
                if suffix=='async.dwf':assert wave.read_bytes()==(work/(backend+'-'+mode+'.dwf')).read_bytes()
                report['captures']+=1
        if backend=='parallel':assert json.loads((work/'parallel.json').read_text())['parallel']['partitions']==1
    if name=='rollback':
        code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
        replacement='''
s.run_until(3);
if(s.predict_until(7,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("unexpected clocking commit");
if(!s.predict_until(8,[](Sim&){},[](const Sim&){return true;},[](Sim&){}))throw std::runtime_error("missing clocking commit");
s.run();
'''
        cpp=work/'replay.cpp';cpp.write_text(code.replace('\ns.run();\n',replacement));native(cpp,work/'replay',work,'replay-compile')
        wave=work/'replay.dwf';wave.unlink(missing_ok=True)
        assert run([work/'replay','--waveform',wave,'--wave-mode','ordered','--wave-async'],work,'replay-run').splitlines()==wanted
        assert stream(wave)==reference['ordered'];report['captures']+=1;report['rollbacks']+=1;report['commits']+=1
        replacement='''
for(;;) {try{s.run();break;}catch(const InstructionBudgetExhausted&){s.limit+=7;}}
'''
        cpp=work/'resume.cpp';cpp.write_text(code.replace('\ns.run();\n',replacement));native(cpp,work/'resume',work,'resume-compile')
        for limit in range(65):
            wave=work/('resume-'+str(limit)+'.vcd');wave.unlink(missing_ok=True)
            assert run([work/'resume','--max-events',limit,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,'resume-'+str(limit)).splitlines()==wanted
            assert stream(wave)==reference['ordered'],('budget cut',limit)
            report['captures']+=1;report['budget_resumes']+=1
    report['models'][name]=dict(status='PASS',source_sha256=hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest())
    save();print('PASS clocking',name,flush=True)
for name,case in json.loads((fixtures/'negative.json').read_text()).items():
    work=out/name;work.mkdir(exist_ok=True);source=work/'bad.sv';source.write_text(case['body']+'\n')
    cpp=work/'bad.cpp';cpp.unlink(missing_ok=True)
    run([compiler,source,'--emit-only','--emit-cpp',cpp],work,'reject',False)
    assert case['diagnostic'] in (work/'reject.stderr').read_text(),name
    assert not cpp.exists();report['negative_cases']+=1;save()
work=out/'multiple_edges';work.mkdir(exist_ok=True)
source=work/'bad.sv';source.write_text('module top;bit clk=0;clocking cb @(posedge clk);endclocking initial begin #1;clk=1;clk=0;clk=1;end endmodule\n')
run([compiler,source,'-o',work/'model'],work,'compile')
run([work/'model'],work,'run',False)
assert 'multiple clocking edges in one time slot' in (work/'run.stderr').read_text()
report['runtime_errors']=1
report['status']='PASS';save();print(json.dumps(report),flush=True)
