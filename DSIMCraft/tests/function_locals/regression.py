"""Cached automatic function locals: four states, full traces, exact budgets and replay."""
from pathlib import Path
import json, subprocess, sys

ROOT = Path(__file__).resolve().parents[2]
compiler = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve(); out.mkdir(parents=True, exist_ok=True)
config_path = Path(sys.argv[3]) if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config = {x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in config_path.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read, declarations

report = {'status':'RUNNING','captures':0,'budget_comparisons':0,'predictions':0}
def run(args, label):
    p = subprocess.run(list(map(str,args)), cwd=out, capture_output=True, text=True, timeout=240)
    (out/(label+'.stdout')).write_text(p.stdout);(out/(label+'.stderr')).write_text(p.stderr)
    assert p.returncode==0,(label,p.returncode,p.stdout,p.stderr[-2000:])
    return p.stdout
def build(code, label, reference=False):
    path = out/(label+'.cpp');path.write_text(code)
    run(['c++','-std=c++17','-O2','-pthread',*(['-DDSIM_RTL_REFERENCE_FUNCTION_LOCALS=1'] if reference else []),'-I'+config['DSIM_ZSTD_INCLUDE'],path,config['DSIM_ZSTD_LIBRARY'],'-o',out/label],label+'-compile')
    return out/label
def streams(path):
    meta,events=read(path);values=[[] for _ in meta['signals']]
    for t,k,v in events:
        if k=='value':values[v[0]].append((t,v[1]))
    return {key:(width,ranges,values[i]) for key,(i,width,ranges) in declarations(meta).items()}
try:
    expected = None; wave_refs={}
    for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
        for wave in [False,True]:
            stem=backend+('-wave' if wave else '')
            run([compiler,ROOT/'tests/function_locals/scalars.sv',*flags,*(['--wave-support'] if wave else []),'--emit-only','--emit-cpp',out/(stem+'.cpp')],stem+'-lower')
            code=(out/(stem+'.cpp')).read_text()
            assert '// Cached automatic scalar function storage.' in code
            instrumented=code.replace('int main(', 'uint64_t function_cache_entries=0;\nint main(')
            instrumented=instrumented.replace('// Cached automatic scalar function storage.', '++function_cache_entries;// Cached automatic scalar function storage.')
            assert instrumented.count('\ns.run();\n')==1
            instrumented=instrumented.replace('\ns.run();\n','\ns.run();\nstd::cerr<<"CACHE "<<function_cache_entries<<"\\n";\n')
            native=build(instrumented,stem);reference=build(code,stem+'-reference',True)
            for mode in (['ordered','settled'] if wave else ['plain']):
                results=[]
                for label,binary in [('native',native),('reference',reference)]:
                    path=out/(stem+'-'+label+'-'+mode+'.vcd')
                    text=run([binary,*(['--waveform',path,'--wave-format','vcd','--wave-mode',mode] if wave else [])],stem+'-'+label+'-'+mode)
                    if expected is None:expected=text
                    assert text==expected,(stem,label,mode,text,expected)
                    results.append((text,streams(path) if wave else None))
                    if wave:report['captures']+=1
                    if label=='native':
                        entries=int((out/(stem+'-'+label+'-'+mode+'.stderr')).read_text().split('CACHE ')[1])
                        assert (entries==0 if wave else entries==72),(stem,entries)
                assert results[0]==results[1],(stem,mode)
                if wave:
                    if backend=='serial':wave_refs[mode]=results[0]
                    else:assert results[0]==wave_refs[mode],(stem,mode)
    code=(out/'serial.cpp').read_text()
    probe='''
try{s.run();}catch(const std::exception& e){std::cout<<"BUDGET "<<s.executed_steps()<<" "<<e.what()<<"\\n";}
std::cout<<"STATE "<<s.now<<" "<<s.executed_steps();for(const auto& item:s.signals)std::cout<<" "<<item.value.a<<":"<<item.value.b<<":"<<item.value.w;std::cout<<"\\n";
'''
    native=build(code.replace('\ns.run();\n',probe),'budget')
    reference=build(code.replace('\ns.run();\n',probe),'budget-reference',True)
    for budget in [*range(180),255,256,511,512,1024,4096,100000]:
        a=run([native,'--max-events',budget],'budget-'+str(budget))
        b=run([reference,'--max-events',budget],'budget-reference-'+str(budget))
        assert a==b,(budget,a,b)
        report['budget_comparisons']+=1
    for accept in [False,True]:
        patch='\nbool accepted=s.predict_until(11000,[](Sim&){},[](const Sim&){return '+str(accept).lower()+';},[](Sim&){});\n'
        patch+='if(accepted!='+str(accept).lower()+')throw std::runtime_error("prediction mismatch");\ns.run();\n'
        binary=build(code.replace('\ns.run();\n',patch),'predict-'+str(accept))
        assert run([binary],'predict-'+str(accept)+'-run')==expected
        report['predictions']+=1
    report.update(status='PASS',output=expected.splitlines())
finally:
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
