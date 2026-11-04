"""Scalar edge dispatch: complete transitions, budget boundaries and replay."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];fixtures=ROOT/'tests/static_net_drives'
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations
report={'status':'RUNNING','captures':0,'budget_comparisons':0,'predictions':0,'models':{}}
def run(cmd,work,label):
 p=subprocess.run(list(map(str,cmd)),cwd=work,text=True,capture_output=True,timeout=240)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stdout,p.stderr[-3000:]);return p.stdout

def build(code,work,label,reference=False):
 cpp=work/(label+'.cpp');cpp.write_text(code)
 run(['c++','-std=c++17','-O2','-pthread',*(['-DDSIM_REFERENCE_EDGE_MASKS=1'] if reference else []),'-I'+config['DSIM_ZSTD_INCLUDE'],cpp,config['DSIM_ZSTD_LIBRARY'],'-o',work/label],work,label+'-compile');return work/label

def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 decl=declarations(meta);names={i:tuple(sorted(k for k,v in decl.items() if v[0]==i)) for i in range(len(values))};ordered=[]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]));ordered.append((t,names[p[0]],p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in decl.items()},ordered

try:
 for name in ['edges','networks','force','wide']:
  work=out/name;work.mkdir(exist_ok=True);refs={}
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,(ROOT/'tests/scalar_edges/edges.sv' if name=='edges' else fixtures/(name+'.sv')),*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-lower')
   code=(work/(backend+'.cpp')).read_text();ir=json.loads((work/(backend+'.json')).read_text())
   if backend=='serial':build(code,work,'reference',True)
   for variant in ([backend,'reference'] if backend=='serial' else [backend]):
    for mode in ['ordered','settled']:
     wave=work/(variant+'-'+mode+'.vcd');wave.unlink(missing_ok=True)
     text=run([work/variant,'--waveform',wave,'--wave-format','vcd','--wave-mode',mode],work,variant+'-'+mode)
     current=(text,stream(wave))
     if variant=='serial':refs[mode]=current
     else:assert current==refs[mode],(name,variant,mode)
     report['captures']+=1
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  text=refs['ordered'][0]
  if name=='edges':assert sum(line.startswith('TRACE edge ') and not line.startswith('TRACE edge complete ') for line in text.splitlines())==32 and 'TRACE edge complete 32' in text,text
  elif name=='networks':assert text.count('TRACE nets ')==12 and text.endswith('TRACE complete 23 6 8\n'),text
  elif name=='force':assert text=='TRACE force 34\n',text
  else:assert text=='TRACE wide x123z45612345678abcd0123456789ab\n',text
  probe='''
try{s.run();}catch(const std::exception& e){std::cout<<"BUDGET "<<s.executed_steps()<<" "<<e.what()<<"\\n";}
std::cout<<"STATE "<<s.now<<" "<<s.executed_steps();for(const auto& item:s.signals){std::cout<<" ";for(int bit=0;bit<item.value.w;++bit)std::cout<<item.value.bit(bit);}std::cout<<"\\n";
'''
  a=build(code.replace('\ns.run();\n',probe),work,'budget');b=build(code.replace('\ns.run();\n',probe),work,'budget-reference',True)
  for limit in [*range(257),511,512,513,1024,4096,100000]:
   assert run([a,'--max-events',limit],work,'budget-'+str(limit))==run([b,'--max-events',limit],work,'reference-'+str(limit)),(name,limit)
   report['budget_comparisons']+=1
  for accept in [False,True]:
   patch='\nbool accepted=s.predict_until(12000,[](Sim&){},[](const Sim&){return '+str(accept).lower()+';},[](Sim&){});\n'
   patch+='if(accepted!='+str(accept).lower()+'||s.prediction_stats.'+('commits' if accept else 'rollbacks')+'!=1)throw std::runtime_error("prediction mismatch");\ns.run();\n'
   label='predict-'+str(accept);binary=build(code.replace('\ns.run();\n',patch),work,label)
   wave=work/(label+'.vcd');wave.unlink(missing_ok=True)
   current=(run([binary,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,label+'-run'),stream(wave))
   assert current==refs['ordered'],(name,label);report['captures']+=1;report['predictions']+=1
  report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256((ROOT/'tests/scalar_edges/edges.sv' if name=='edges' else fixtures/(name+'.sv')).read_bytes()).hexdigest()}
  print('PASS scalar edges',name,flush=True)
 report['status']='PASS'
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
