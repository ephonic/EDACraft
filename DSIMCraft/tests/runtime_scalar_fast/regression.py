"""Known-bit function loops versus the four-state path, observers, budgets and replay."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations

def run(cmd,label):
 p=subprocess.run(list(map(str,cmd)),cwd=out,capture_output=True,text=True,timeout=240)
 (out/(label+'.stdout')).write_text(p.stdout);(out/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stderr[-2000:]);return p.stdout

def build(code,label):
 cpp=out/(label+'.cpp');cpp.write_text(code)
 run(['c++','-std=c++17','-O2','-pthread','-I'+config['DSIM_ZSTD_INCLUDE'],cpp,config['DSIM_ZSTD_LIBRARY'],'-o',out/label],label+'-compile');return out/label

def streams(p):
 meta,events=read(p);values=[[] for _ in meta['signals']]
 for t,k,v in events:
  if k=='value':values[v[0]].append((t,v[1]))
 return {key:(width,ranges,values[i]) for key,(i,width,ranges) in declarations(meta).items()}
# An independent integer oracle for every fully known output. Unknown cases are
# retained explicitly and also checked against VCS in the release evidence.
crc=0x12345678
for _ in range(8):crc=(crc>>1)^(0xedb88320 if crc&1 else 0)
wanted=[f'TRACE crc {crc:08x}','TRACE z xxxxxxxx','TRACE x 00xxxx00']
for count in range(66):
 t=0xfedcba9876543210
 for _ in range(3):t=(((t<<count)^(t>>count))&((1<<64)-1)) if count<64 else 0
 wanted.append(f'TRACE shift {count} {t:016x} 0000000000000000 00000000000000ff 000000000000017e')
report={'status':'RUNNING','captures':0,'budget_comparisons':0,'prediction':[]}
try:
 refs={}
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  for wave in [False,True]:
   stem=backend+('-wave' if wave else '')
   run([compiler,fixtures/'functions.sv',*flags,*(['--wave-support'] if wave else []),'--emit-cpp',out/(stem+'.cpp'),'-o',out/stem],stem+'-lower')
   for mode in (['ordered','settled'] if wave else ['plain']):
    vcd=out/(stem+'-'+mode+'.vcd')
    text=run([out/stem,*(['--waveform',vcd,'--wave-format','vcd','--wave-mode',mode] if wave else [])],stem+'-'+mode)
    assert text.splitlines()==wanted,(stem,mode,text)
    if wave:
     current=streams(vcd)
     if backend=='serial':refs[mode]=current
     else:assert current==refs[mode],(backend,mode,'signal timelines')
     report['captures']+=1
 code=(out/'serial.cpp').read_text();assert code.count('// Native integral loop;')>=3
 fallback=code.replace('if(s.integral_loop_ready(','if(false && s.integral_loop_ready(')
 assert run([build(fallback,'fallback')],'fallback-run').splitlines()==wanted
 for accept in [False,True]:
  patch='\nbool accepted=s.predict_until(100000,[](Sim&){},[](const Sim&){return '+str(accept).lower()+';},[](Sim&){});\n'
  patch+='if(accepted!='+str(accept).lower()+'||s.prediction_stats.'+('commits' if accept else 'rollbacks')+'!=1)throw std::runtime_error("prediction mismatch");\ns.run();\n'
  probe=code.replace('\ns.run();\n',patch)
  assert run([build(probe,'predict-'+str(accept))],'predict-run-'+str(accept)).splitlines()==wanted
  report['prediction'].append('accept' if accept else 'reject')
 probe='''
try{s.run();}catch(const std::exception& e){std::cout<<"BUDGET "<<s.executed_steps()<<" "<<e.what()<<"\\n";}
std::cout<<"STATE "<<s.executed_steps();for(const auto& item:s.signals)std::cout<<" "<<item.value.a<<":"<<item.value.b;std::cout<<"\\n";
'''
 native=build(code.replace('\ns.run();\n',probe),'budget-native');slow=build(fallback.replace('\ns.run();\n',probe),'budget-reference')
 for limit in [*range(161),255,256,257,1024,4096,100000]:
  assert run([native,'--max-events',limit],'native-'+str(limit))==run([slow,'--max-events',limit],'reference-'+str(limit)),limit
  report['budget_comparisons']+=1
 report.update(status='PASS',trace=wanted)
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS scalar functions,',report['captures'],'VCD captures,',report['budget_comparisons'],'exact budget/state comparisons, accepted/rejected prediction')
