"""Compare deferred diagnostic order, ordered waves and interrupted execution."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]) if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read
report={'status':'RUNNING','captures':0,'budget_comparisons':0,'kernel_checks':0}
def run(args,work,label):
 p=subprocess.run(list(map(str,args)),cwd=work,text=True,capture_output=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stdout,p.stderr[-2000:]);return p.stdout
def build(source,work,label,reference=False,kernel=False):
 flags=['-DDSIM_REFERENCE_SELECTION_FLUSH=1'] if reference else []
 if kernel:flags+=['-I'+str(ROOT/'include')]
 run(['c++','-std=c++17','-O2','-UNDEBUG','-pthread',*flags,'-I'+config['DSIM_ZSTD_INCLUDE'],source,config['DSIM_ZSTD_LIBRARY'],'-o',work/label],work,label+'-compile')
 return work/label
try:
 for ref in [False,True]:
  label='kernel-reference' if ref else 'kernel-native'
  binary=build(ROOT/'tests/selection_flush/kernel.cpp',out,label,ref,True)
  assert run([binary],out,label+'-run')=='PASS 30 pending-report budget/checkpoint/prediction checks\n'
  report['kernel_checks']+=30
 for name in ['branches','cases','events','glitches']:
  work=out/name;work.mkdir(exist_ok=True)
  run([compiler,ROOT/'tests/selection_checks'/(name+'.sv'),'--wave-support','--emit-only','--emit-cpp',work/'model.cpp'],work,'lower')
  code=(work/'model.cpp').read_text();assert code.count('\ns.run();\n')==1
  for ref in [False,True]:build(work/'model.cpp',work,'reference' if ref else 'native',ref)
  for mode in ['ordered','settled']:
   observations=[]
   for label in ['native','reference']:
    wave=work/(label+'-'+mode+'.vcd');wave.unlink(missing_ok=True)
    output=run([work/label,'--waveform',wave,'--wave-format','vcd','--wave-mode',mode],work,label+'-'+mode)
    observations.append((output,read(wave)));report['captures']+=1
   assert observations[0]==observations[1],(name,mode)
  probe='''
try{s.run();}catch(const std::exception& e){std::cout<<"BUDGET "<<s.executed_steps()<<" "<<e.what()<<"\\n";}
std::cout<<"STATE "<<s.now<<" "<<s.executed_steps();for(const auto& signal:s.signals){std::cout<<" ";for(int bit=0;bit<signal.value.w;++bit)std::cout<<signal.value.bit(bit);}std::cout<<"\\n";
'''
  (work/'budget.cpp').write_text(code.replace('\ns.run();\n',probe))
  for ref in [False,True]:build(work/'budget.cpp',work,'budget-reference' if ref else 'budget',ref)
  for limit in [*range(97),127,255,511,1024,100000]:
   a=run([work/'budget','--max-events',limit],work,'budget-'+str(limit))
   b=run([work/'budget-reference','--max-events',limit],work,'reference-'+str(limit))
   assert a==b,(name,limit);report['budget_comparisons']+=1
  print('PASS selection flush',name,flush=True)
 report['status']='PASS'
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
