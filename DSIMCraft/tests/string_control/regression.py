"""String case and character access: state, backend agreement and replay."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations

def run(command,work,label):
 p=subprocess.run(list(map(str,command)),cwd=work,capture_output=True,text=True,timeout=240)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout

def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}

def compile_cpp(code,work,label):
 path=work/(label+'.cpp');path.write_text(code)
 run(['c++','-std=c++17','-O2','-pthread','-I'+config['DSIM_ZSTD_INCLUDE'],path,config['DSIM_ZSTD_LIBRARY'],'-o',work/label],work,label+'-compile')
 return work/label

expected=json.loads((fixtures/'expected.json').read_text())
report={'status':'RUNNING','models':{},'captures':0,'rollbacks':0,'budget_comparisons':0}
try:
 for name,wanted in expected.items():
  work=out/name;work.mkdir(exist_ok=True);references={}
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   for wave_support in [False,True]:
    stem=backend+('-wave' if wave_support else '')
    run([compiler,fixtures/(name+'.sv'),*flags,*(['--wave-support'] if wave_support else []),'--emit-cpp',work/(stem+'.cpp'),'--emit-ir',work/(stem+'.json'),'-o',work/stem],work,stem+'-compile')
    for mode in (['ordered','settled'] if wave_support else ['plain']):
     wave=work/(backend+'-'+mode+'.vcd');wave.unlink(missing_ok=True)
     text=run([work/stem,*(['--waveform',wave,'--wave-format','vcd','--wave-mode',mode] if wave_support else [])],work,backend+'-'+mode)
     assert text.splitlines()==wanted,(name,backend,mode,text,wanted)
     if wave_support:
      current=streams(wave)
      if backend=='serial':references[mode]=current
      else:assert current==references[mode],(name,backend,mode,'full signal stream')
      report['captures']+=1
  code=(work/'serial.cpp').read_text()
  assert code.count('\ns.run();\n')==1
  replay=code.replace('\ns.run();\n','''
if(s.predict_until(100000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
''')
  assert run([compile_cpp(replay,work,'replay')],work,'replay-run').splitlines()==wanted,(name,'replay')
  report['rollbacks']+=1
  if name in ['arithmetic','widths']:
   assert '// Native integral loop;' in code,(name,'loop not lowered')
   probe=code.replace('\ns.run();\n','''
try{s.run();}catch(const std::exception& e){std::cout<<"BUDGET "<<s.executed_steps()<<" "<<e.what()<<"\\n";}
std::cout<<"STATE "<<s.executed_steps();for(const auto& item:s.signals)std::cout<<" "<<item.value.a<<":"<<item.value.b;std::cout<<"\\n";
''')
   native=compile_cpp(probe,work,'budget-native')
   slow=compile_cpp(probe.replace('if(s.integral_loop_ready(','if(false && s.integral_loop_ready('),work,'budget-reference')
   for limit in [*range(0,41),63,64,65,119,120,121,40020,1000000]:
    a=run([native,'--max-events',limit],work,'budget-native-'+str(limit))
    b=run([slow,'--max-events',limit],work,'budget-reference-'+str(limit))
    assert a==b,(name,limit,a,b);report['budget_comparisons']+=1
  report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),'output':wanted}
  print('PASS',fixtures.name,name,flush=True)
 if fixtures.name=='integral_loops':
  ir=json.loads((out/'parallel/parallel.json').read_text());assert ir['parallel']['partitions']==2,ir['parallel']
 negatives={
  'index_type':('string s;initial $display("%h",s[s]);','integral value'),
  'range':("string s;initial s[2:0]=8'h41;","one character index"),
  'nba':("string s;initial s[0]<=8'h41;","blocking assignment"),
  'const_write':("task automatic f(const ref string s);s[0]=8'h41;endtask string s;initial f(s);","const ref"),
  'case_mixed':('string s;initial case(s) 12:$finish;endcase','compatible string'),
  'casez':('string s;initial casez(s) "a":$finish;endcase','exact case'),
 }
 for name,(body,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text('module top;'+body+' endmodule\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  p=subprocess.run([str(compiler),str(source),'--emit-only','--emit-cpp',str(dest)],capture_output=True,text=True)
  (out/(name+'.stderr')).write_text(p.stderr)
  assert p.returncode==1 and diagnostic in p.stderr and not dest.exists(),(name,p.returncode,p.stdout,p.stderr)
 report['negative_cases']=len(negatives)
 report['status']='PASS'
except Exception as error:
 report.update(status='FAIL',error=str(error));raise
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS',fixtures.name,len(report['models']),'models,',report['captures'],'VCD captures,',report['rollbacks'],'rollbacks,',report['budget_comparisons'],'budget comparisons')
