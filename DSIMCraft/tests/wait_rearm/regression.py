"""Ordinary RTL wait reuse: complete event streams, exact budgets and rollback."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations
wanted=['TRACE lists 16 48 55 16'];report={'status':'RUNNING','captures':0,'budget_comparisons':0,'predictions':[]}
def run(cmd,label):
 p=subprocess.run(list(map(str,cmd)),cwd=out,capture_output=True,text=True,timeout=240)
 (out/(label+'.stdout')).write_text(p.stdout);(out/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stdout,p.stderr);return p.stdout

def build(code,label,flags=[]):
 cpp=out/(label+'.cpp');cpp.write_text(code)
 run(['c++','-std=c++17','-O2','-UNDEBUG','-pthread',*flags,'-I'+config['DSIM_ZSTD_INCLUDE'],cpp,config['DSIM_ZSTD_LIBRARY'],'-o',out/label],label+'-compile');return out/label

def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
try:
 run(['c++','-std=c++17','-O2','-UNDEBUG','-I'+str(ROOT/'include'),fixtures/'kernel.cpp','-o',out/'kernel'],'kernel-compile');run([out/'kernel'],'kernel-run')
 for label,flags in [('fork-kernel',['-DDSIM_FORK_JOIN_ENABLED=1']),('fork-reference',['-DDSIM_FORK_JOIN_ENABLED=1','-DDSIM_DISABLE_WAIT_REARM_CACHE=1'])]:
  run(['c++','-std=c++17','-O2','-UNDEBUG',*flags,'-I'+str(ROOT/'include'),fixtures/'kernel.cpp','-o',out/label],label+'-compile');run([out/label],label+'-run')
 refs={}
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,fixtures/'lists.sv',*flags,'--wave-support','--emit-cpp',out/(backend+'.cpp'),'-o',out/backend],backend+'-lower')
  code=(out/(backend+'.cpp')).read_text()
  for macro in ['DSIM_PROCESS_CONTROL_ENABLED','DSIM_DYNAMIC_FORK_ENABLED','DSIM_EXPRESSION_EVENTS_ENABLED','DSIM_NAMED_EVENTS_ENABLED','DSIM_WAIT_ORDER_ENABLED']:
   assert '#define '+macro not in code,macro
  if backend=='serial':build(code,'reference',['-DDSIM_DISABLE_WAIT_REARM_CACHE=1'])
  for variant in ([backend,'reference'] if backend=='serial' else [backend]):
   for mode in ['ordered','settled']:
    vcd=out/(variant+'-'+mode+'.vcd')
    assert run([out/variant,'--waveform',vcd,'--wave-format','vcd','--wave-mode',mode],variant+'-'+mode).splitlines()==wanted
    current=stream(vcd)
    if variant=='serial':refs[mode]=current
    else:assert current==refs[mode],(variant,mode)
    report['captures']+=1
 code=(out/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
 for accept in [False,True]:
  patch='\nbool accepted=s.predict_until(100000,[](Sim&){},[](const Sim&){return '+str(accept).lower()+';},[](Sim&){});\n'
  patch+='if(accepted!='+str(accept).lower()+'||s.prediction_stats.'+('commits' if accept else 'rollbacks')+'!=1)throw std::runtime_error("prediction mismatch");\ns.run();\n'
  label='predict-'+str(accept);binary=build(code.replace('\ns.run();\n',patch),label)
  vcd=out/(label+'.vcd');assert run([binary,'--waveform',vcd,'--wave-format','vcd','--wave-mode','ordered'],label+'-run').splitlines()==wanted
  assert stream(vcd)==refs['ordered'],label
  report['captures']+=1;report['predictions'].append('accept' if accept else 'reject')
 probe='''
try{s.run();}catch(const std::exception& e){std::cout<<"BUDGET "<<s.executed_steps()<<" "<<e.what()<<"\\n";}
std::cout<<"STATE "<<s.now<<" "<<s.executed_steps();for(const auto& item:s.signals)std::cout<<" "<<item.value.a<<":"<<item.value.b;std::cout<<"\\n";
'''
 active=build(code.replace('\ns.run();\n',probe),'budget-cached');reference=build(code.replace('\ns.run();\n',probe),'budget-reference',['-DDSIM_DISABLE_WAIT_REARM_CACHE=1'])
 for limit in [*range(257),511,512,513,1024,4096]:
  assert run([active,'--max-events',limit],'cached-'+str(limit))==run([reference,'--max-events',limit],'reference-'+str(limit)),limit
  report['budget_comparisons']+=1
 report.update(status='PASS',output=wanted,serial_cpp_sha256=hashlib.sha256(code.encode()).hexdigest())
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS wait rearm,',report['captures'],'complete VCDs,',report['budget_comparisons'],'exact budget/state comparisons, prediction commit/rollback')
