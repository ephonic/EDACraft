"""Lone wake dispatch preserves FIFO, delayed NBA, waves and interrupted replay."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]) if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations
report={'status':'RUNNING','models':{},'captures':0,'budget_comparisons':0,'predictions':0,'kernel_states':0}
def run(args,work,label):
 p=subprocess.run(list(map(str,args)),cwd=work,text=True,capture_output=True,timeout=240)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stdout,p.stderr[-2000:]);return p.stdout
def build(code,work,label,reference=False):
 source=work/(label+'.cpp');source.write_text(code)
 run(['c++','-std=c++17','-O2','-pthread',*(['-DDSIM_REFERENCE_WAKE_DISPATCH=1'] if reference else []),'-I'+config['DSIM_ZSTD_INCLUDE'],source,config['DSIM_ZSTD_LIBRARY'],'-o',work/label],work,label+'-compile');return work/label
def capture(binary,work,label,mode='ordered'):
 wave=work/(label+'.vcd');wave.unlink(missing_ok=True)
 text=run([binary,'--waveform',wave,'--wave-format','vcd','--wave-mode',mode],work,label)
 meta,events=read(wave);values=[[] for _ in meta['signals']]
 for t,kind,value in events:
  if kind=='value':values[value[0]].append((t,value[1]))
 return text,{name:(width,ranges,values[i]) for name,(i,width,ranges) in declarations(meta).items()}
try:
 kernels=[]
 for ref in [False,True]:
  label='kernel-reference' if ref else 'kernel-native'
  run(['c++','-std=c++17','-O2','-UNDEBUG','-pthread','-I'+str(ROOT/'include'),*(['-DDSIM_REFERENCE_WAKE_DISPATCH=1'] if ref else []),ROOT/'tests/wake_dispatch/kernel.cpp','-o',out/label],out,label+'-compile')
  kernels.append(run([out/label],out,label+'-run'))
 assert kernels[0]==kernels[1]
 assert kernels[0].endswith('PASS 512 wake, budget, checkpoint and prediction states\n')
 report['kernel_states']=512
 for name in (sys.argv[4:] or ['timing']):
  work=out/name;work.mkdir(exist_ok=True);references={}
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,ROOT/'tests/wake_dispatch'/(name+'.sv'),'--wave-support',*flags,'--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-lower')
   code=(work/(backend+'.cpp')).read_text();ir=json.loads((work/(backend+'.json')).read_text())
   if backend=='parallel':assert ir['parallel']['partitions']==2,ir['parallel']
   if backend=='serial':
    build(code,work,'reference',True)
   for variant in ([backend,'reference'] if backend=='serial' else [backend]):
    for mode in ['ordered','settled']:
     obs=capture(work/variant,work,variant+'-'+mode,mode)
     if variant=='serial':references[mode]=obs
     else:
      assert obs==references[mode],(name,variant,mode)
      if variant in ['reference','wheel']:
       assert read(work/(variant+'-'+mode+'.vcd'))==read(work/('serial-'+mode+'.vcd')),(name,variant,mode,'complete ordered stream')
     report['captures']+=1
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  probe='''
try{s.run();}catch(const std::exception& e){std::cout<<"BUDGET "<<s.executed_steps()<<" "<<e.what()<<"\\n";}
std::cout<<"STATE "<<s.now<<" "<<s.executed_steps();for(const auto& signal:s.signals){std::cout<<" ";for(int bit=0;bit<signal.value.w;++bit)std::cout<<signal.value.bit(bit);}std::cout<<"\\n";
'''
  a=build(code.replace('\ns.run();\n',probe),work,'budget');b=build(code.replace('\ns.run();\n',probe),work,'budget-reference',True)
  for limit in [*range(193),255,511,1024,100000]:
   assert run([a,'--max-events',limit],work,'budget-'+str(limit))==run([b,'--max-events',limit],work,'reference-'+str(limit)),(name,limit)
   report['budget_comparisons']+=1
  if name=='timing':
   for accept in [False,True]:
    patch='\nif(s.predict_until(8001,[](Sim&){},[](const Sim&){return '+str(accept).lower()+';},[](Sim&){})!='+str(accept).lower()+')throw std::runtime_error("prediction mismatch");\ns.run();\n'
    label='predict-'+str(accept);binary=build(code.replace('\ns.run();\n',patch),work,label)
    assert capture(binary,work,label+'-run')==references['ordered'],(name,label)
    report['captures']+=1;report['predictions']+=1
  report['models'][name]={'status':'PASS','regions':json.loads((work/'serial.json').read_text())['comb_regions']}
  print('PASS wake dispatch',name,flush=True)
 report['status']='PASS'
except Exception as error:
 report.update(status='FAIL',error=str(error));raise
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
