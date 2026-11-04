"""Word fusion versus the original four-state expressions at observable boundaries."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations
report={'status':'RUNNING','captures':0,'budget_comparisons':0,'predictions':0,'models':{}}
def run(cmd,work,label):
 p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=240)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stdout,p.stderr[-2000:]);return p.stdout
def build(code,work,label,reference=False):
 path=work/(label+'.cpp');path.write_text(code)
 run(['c++','-std=c++17','-O2','-pthread',*(['-DDSIM_RTL_REFERENCE_EXPRESSIONS=1'] if reference else []),'-I'+config['DSIM_ZSTD_INCLUDE'],path,config['DSIM_ZSTD_LIBRARY'],'-o',work/label],work,label+'-compile');return work/label
def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,v in events:
  if k=='value':values[v[0]].append((t,v[1]))
 return {key:(width,ranges,values[i]) for key,(i,width,ranges) in declarations(meta).items()}
try:
 for name,source in [('expressions',fixtures/'expressions.sv'),('widths',ROOT/'tests/integral_loops/widths.sv'),('scopes',ROOT/'tests/fork_join/scopes.sv')]:
  work=out/name;work.mkdir(exist_ok=True);refs={}
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,source,*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-lower')
   code=(work/(backend+'.cpp')).read_text()
   if name=='expressions':assert 'DSIM_RTL_REFERENCE_EXPRESSIONS' in code
   if backend=='serial':build(code,work,'reference',True)
   for variant in ([backend,'reference'] if backend=='serial' else [backend]):
    for mode in ['ordered','settled']:
     wave=work/(variant+'-'+mode+'.vcd')
     text=run([work/variant,'--waveform',wave,'--wave-format','vcd','--wave-mode',mode],work,variant+'-'+mode)
     current=(text,streams(wave))
     if variant=='serial':refs[mode]=current
     else:assert current==refs[mode],(name,variant,mode)
     report['captures']+=1
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  for accept in [False,True]:
   patch='\nbool accepted=s.predict_until(1000000,[](Sim&){},[](const Sim&){return '+str(accept).lower()+';},[](Sim&){});\n'
   patch+='if(accepted!='+str(accept).lower()+')throw std::runtime_error("prediction mismatch");\ns.run();\n'
   label='predict-'+str(accept);binary=build(code.replace('\ns.run();\n',patch),work,label)
   wave=work/(label+'.vcd');text=run([binary,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,label+'-run')
   assert (text,streams(wave))==refs['ordered'],(name,label);report['captures']+=1;report['predictions']+=1
  probe='''
try{s.run();}catch(const std::exception& e){std::cout<<"BUDGET "<<s.executed_steps()<<" "<<e.what()<<"\\n";}
std::cout<<"STATE "<<s.now<<" "<<s.executed_steps();for(const auto& item:s.signals)std::cout<<" "<<item.value.a<<":"<<item.value.b;std::cout<<"\\n";
'''
  patched=code.replace('\ns.run();\n',probe)
  a=build(patched,work,'budget');b=build(patched,work,'budget-reference',True)
  for limit in [*range(80),127,255,256,511,1024,4096,100000]:
   assert run([a,'--max-events',limit],work,'budget-'+str(limit))==run([b,'--max-events',limit],work,'reference-'+str(limit)),(name,limit)
   report['budget_comparisons']+=1
  report['models'][name]='PASS';print('PASS runtime_windows',name,flush=True)
 # Four real generated RTL partitions, with time precision in picoseconds.
 sys.path.insert(0,str(ROOT/'tests/parallel_arithmetic'));from probe import instrument
 work=out/'lanes';work.mkdir(exist_ok=True);reference=None
 for workers in [0,1,4]:
  stem='lanes-'+str(workers);cpp=work/(stem+'.cpp');ir=work/(stem+'.json')
  run([compiler,ROOT/'tests/parallel_arithmetic/lanes.sv','--wave-support',*(['--threads',workers] if workers else []),'--emit-only','--emit-cpp',cpp,'--emit-ir',ir],work,stem+'-lower')
  data=json.loads(ir.read_text());exe=build(instrument(cpp.read_text(),data),work,stem)
  if workers==4:assert data['parallel']['partitions']==4
  for window in ([1,1024,1000000] if workers else [None]):
   for mode in ['ordered','settled']:
    label=stem+'-'+str(window)+'-'+mode;wave=work/(label+'.vcd')
    text=run([exe,*(['--parallel-window',window,'--parallel-stats'] if workers else []),'--waveform',wave,'--wave-format','vcd','--wave-mode',mode],work,label)
    current=(text,streams(wave))
    if workers==0:
     if reference is None:reference={}
     reference[mode]=current
    else:assert current==reference[mode],(workers,window,mode)
    if workers==4 and window==1000000:
     stats=json.loads((work/(label+'.stderr')).read_text().removeprefix('PARALLEL '));assert stats['windows']==2,stats
    report['captures']+=1
  if workers:
   for index,value in enumerate(['0','-1','x','18446744073709551616',None]):
    args=[exe,'--parallel-window']+([] if value is None else [value])
    result=subprocess.run(list(map(str,args)),cwd=work,capture_output=True,text=True,timeout=30)
    assert result.returncode==1,(workers,value,result.stdout,result.stderr)
 report['parallel_partitions']=4
 report['status']='PASS'
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
