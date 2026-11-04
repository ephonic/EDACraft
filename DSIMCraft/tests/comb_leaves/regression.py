"""Direct continuous bodies: ordered events, interruption and replay."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];fixtures=ROOT/'tests/static_net_drives'
activation='--compiled-activation' in sys.argv
if activation:sys.argv.remove('--compiled-activation')
typed='--typed-stores' in sys.argv
if typed:sys.argv.remove('--typed-stores')
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
cxx=config.get('DSIM_MODEL_CXX',config['CMAKE_CXX_COMPILER'])
cxx_args=[cxx,'-std=c++17',config.get('DSIM_MODEL_OPTIMIZATION','-O2'),'-pthread']
if activation:cxx_args.append('-DDSIM_EXPERIMENTAL_COMPILED_ACTIVATION=1')
if typed:cxx_args.append('-DDSIM_EXPERIMENTAL_TYPED_STORES=1')
if Path(cxx).name in ['icpx','icpc']:cxx_args.append('-fp-model=strict')
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations
report={'feature':'typed_stores' if typed else 'compiled_activation' if activation else 'comb_leaves','status':'RUNNING','captures':0,'budget_comparisons':0,'predictions':0,'resumes':0,'resume_reference_errors':0,'models':{}}
def observe(cmd,work,label):
 p=subprocess.run(list(map(str,cmd)),cwd=work,text=True,capture_output=True,timeout=240)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 return p.returncode,p.stdout,p.stderr
def run(cmd,work,label):
 status,text,err=observe(cmd,work,label)
 assert status==0,(label,status,text,err[-3000:]);return text

def build(code,work,label,reference=False):
 cpp=work/(label+'.cpp');cpp.write_text(code)
 run([*cxx_args,*(['-DDSIM_REFERENCE_TYPED_STORES=1' if typed else '-DDSIM_REFERENCE_COMPILED_ACTIVATION=1' if activation else '-DDSIM_REFERENCE_COMB_LEAVES=1'] if reference else []),'-I'+config['DSIM_ZSTD_INCLUDE'],cpp,config['DSIM_ZSTD_LIBRARY'],'-o',work/label],work,label+'-compile');return work/label

def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 decl=declarations(meta);names={i:tuple(sorted(k for k,v in decl.items() if v[0]==i)) for i in range(len(values))};ordered=[]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]));ordered.append((t,names[p[0]],p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in decl.items()},ordered

try:
 for name in (sys.argv[4:] or (['edges','chain','boundaries','cohorts','masked','shared_inputs','networks','force','wide'] if typed else ['edges','chain','boundaries','cohorts','masked','networks','force','wide','controls','branches','cases'] if activation else ['edges','chain','boundaries','cohorts','masked','networks','force','wide'])):
  work=out/name;work.mkdir(exist_ok=True);refs={}
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   if activation:flags += ['--cxx-flag','-DDSIM_EXPERIMENTAL_COMPILED_ACTIVATION=1']
   if typed:flags += ['--cxx-flag','-DDSIM_EXPERIMENTAL_TYPED_STORES=1']
   run([compiler,(ROOT/'tests/compiled_activation'/(name+'.sv') if name in ['controls','branches','cases'] else ROOT/'tests/comb_leaves'/(name+'.sv') if name in ['edges','chain'] else ROOT/'tests/comb_regions'/(name+'.sv') if name in ['cohorts','masked','boundaries','shared_inputs'] else fixtures/(name+'.sv')),*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-lower')
   code=(work/(backend+'.cpp')).read_text();ir=json.loads((work/(backend+'.json')).read_text())
   if backend=='serial':
    if typed and name in ['edges','chain','cohorts','boundaries','masked','shared_inputs']:assert ir['typed_net_store_candidates'] and '#define DSIM_TYPED_STORES_ENABLED 1' in code,(name,'typed store coverage')
    if activation and name in ['edges','chain','controls','branches','cases']:assert ir['compiled_activations'],(name,'compiled activation coverage')
    if activation and name in ['force','wide']:assert not ir['compiled_activations'],(name,'fallback coverage')
    if name=='cases':assert len(ir['compiled_activations'])==4,(name,'nested/unique/clocked/latch case coverage',ir['compiled_activations'])
    if name in ['edges','chain']:assert ir['comb_leaves'],(name,ir)
    if name in ['networks','force','wide']:assert not ir['comb_leaves'],(name,ir)
    build(code,work,'reference',True)
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
  if name=='edges':assert sum(line.startswith('TRACE ') for line in text.splitlines())==4,text
  elif name=='chain':assert text.strip()=='PROBE 0000000b 12345673 5b05b04d 4',text
  elif name=='networks':assert text.count('TRACE nets ')==12 and text.endswith('TRACE complete 23 6 8\n'),text
  elif name=='force':assert text=='TRACE force 34\n',text
  elif name=='wide':assert text=='TRACE wide x123z45612345678abcd0123456789ab\n',text
  elif name=='controls':assert text.strip()=='TRACE notifications 2 3 5 2 2 0000000000000000',text
  elif name=='branches':assert text.startswith('TRACE branches '),text
  elif name=='cases':assert text.count('TRACE cases ')==2 and 'unique case overlap' in text,text
  else:assert json.loads((work/'serial.json').read_text())['comb_regions'],(name,'exercise negative region subscriptions')
  probe='''
try{s.run();}catch(const std::exception& e){std::cout<<"BUDGET "<<s.executed_steps()<<" "<<e.what()<<"\\n";}
std::cout<<"STATE "<<s.now<<" "<<s.executed_steps();for(const auto& item:s.signals){std::cout<<" ";for(int bit=0;bit<item.value.w;++bit)std::cout<<item.value.bit(bit);}std::cout<<"\\n";
'''
  a=build(code.replace('\ns.run();\n',probe),work,'budget');b=build(code.replace('\ns.run();\n',probe),work,'budget-reference',True)
  for limit in [*range(257),511,512,513,1024,4096,100000]:
   assert run([a,'--max-events',limit],work,'budget-'+str(limit))==run([b,'--max-events',limit],work,'reference-'+str(limit)),(name,limit)
   report['budget_comparisons']+=1
  resume_probe='\ntry{s.run();}catch(const std::exception& e){std::cout<<"CUT "<<s.executed_steps()<<"\\n";}\nauto interrupted=s.checkpoint();\nfor(int replay=0;replay<2;++replay){s.restore(interrupted);s.limit=100000000;s.run_until(s.now+12000);std::cout<<"RESUME "<<s.now<<" "<<s.executed_steps();for(const auto& signal:s.signals){std::cout<<" ";for(int bit=0;bit<signal.value.w;++bit)std::cout<<signal.value.bit(bit);}std::cout<<"\\n";}\n'
  x=build(code.replace('\ns.run();\n',resume_probe),work,'resume');y=build(code.replace('\ns.run();\n',resume_probe),work,'resume-reference',True)
  for limit in [*range(65),127,128,129,255,256,257,511]:
   # A budget exception in the legacy interpreter can abandon its popped
   # process, causing a later RTL assertion. Compare those outcomes too;
   # do not call them successful complete simulation resumptions.
   actual=observe([x,'--max-events',limit],work,'resume-'+str(limit))
   expected=observe([y,'--max-events',limit],work,'resume-ref-'+str(limit))
   assert actual==expected,(name,'resume',limit,actual,expected)
   report['resume_reference_errors']+=int(expected[0]!=0)
   report['resumes']+=1
  for accept in [False,True]:
   patch='\nbool accepted=s.predict_until(12000,[](Sim&){},[](const Sim&){return '+str(accept).lower()+';},[](Sim&){});\n'
   patch+='if(accepted!='+str(accept).lower()+'||s.prediction_stats.'+('commits' if accept else 'rollbacks')+'!=1)throw std::runtime_error("prediction mismatch");\ns.run();\n'
   label='predict-'+str(accept);binary=build(code.replace('\ns.run();\n',patch),work,label)
   wave=work/(label+'.vcd');wave.unlink(missing_ok=True)
   current=(run([binary,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,label+'-run'),stream(wave))
   assert current==refs['ordered'],(name,label);report['captures']+=1;report['predictions']+=1
  report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256((ROOT/'tests/compiled_activation'/(name+'.sv') if name in ['controls','branches','cases'] else ROOT/'tests/comb_leaves'/(name+'.sv') if name in ['edges','chain'] else ROOT/'tests/comb_regions'/(name+'.sv') if name in ['cohorts','masked','boundaries','shared_inputs'] else fixtures/(name+'.sv')).read_bytes()).hexdigest()}
  print('PASS direct combinational bodies',name,flush=True)
 kernel=(ROOT/'tests/comb_leaves/batch_kernel.cpp').read_text()
 for label,flags in [('batch-kernel',[]),('batch-kernel-reference',['-DDSIM_REFERENCE_LEAF_BATCH=1'])]:
  cpp=out/(label+'.cpp');cpp.write_text(kernel)
  run([*cxx_args,'-I'+str(ROOT/'include'),*flags,cpp,'-o',out/label],out,label+'-compile')
  value=run([out/label],out,label+'-run')
  if label=='batch-kernel':kernel_reference=value
  else:assert value==kernel_reference,'FIFO batch kernel state mismatch'
 report['batch_kernel_states']=1248
 report['status']='PASS'
except Exception as error:
 report.update(status='FAIL',error=str(error));raise
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
