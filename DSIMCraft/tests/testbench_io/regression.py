"""Runtime plusargs and string formatting: complete streams, partitions, rollback."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations,timeline

def run(command,work,label):
 p=subprocess.run(list(map(str,command)),cwd=work,capture_output=True,text=True,timeout=240)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout

def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
expected=json.loads((fixtures/'expected.json').read_text());scenarios=json.loads((fixtures/'scenarios.json').read_text())
report={'status':'RUNNING','models':{},'captures':0,'rollbacks':0}
try:
 for name,wanted in expected.items():
  work=out/name;work.mkdir(exist_ok=True);reference={};args=scenarios[name]['args']
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,fixtures/(name+'.sv'),*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-compile')
   for mode in ['ordered','settled']:
    wave=work/(backend+'-'+mode+'.vcd');wave.unlink(missing_ok=True)
    # Keep native options interleaved with simulation plusargs.
    text=run([work/backend,'--waveform',wave,*args[:1],'--wave-format','vcd',*args[1:],'--wave-mode',mode],work,backend+'-'+mode)
    assert text.splitlines()==wanted,(name,backend,mode,text,wanted)
    current=stream(wave)
    if backend=='serial':reference[mode]=current
    else:assert current==reference[mode],(name,backend,mode,'complete stream')
    report['captures']+=1
  run([compiler,fixtures/(name+'.sv'),'--emit-cpp',work/'plain.cpp','-o',work/'plain'],work,'plain-compile')
  assert run([work/'plain',*args],work,'plain-run').splitlines()==wanted,(name,'plain')
  if name=='args':
   for variant,row in json.loads((fixtures/'variants.json').read_text()).items():
    for backend in ['serial','wheel','parallel','plain']:
     text=run([work/backend,*row['args']],work,backend+'-'+variant)
     assert text.splitlines()==row['output'],(name,variant,backend,text,row['output'])
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
if(s.predict_until(10000,[](Sim& simulated){simulated.run();},[](const Sim&){return false;},[](Sim& corrected){corrected.run();}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
  run(['c++','-std=c++17','-O2','-pthread','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  wave=work/'replay.vcd';wave.unlink(missing_ok=True)
  assert run([work/'replay',*args,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,'replay-run').splitlines()==wanted,(name,'replay output')
  assert stream(wave)==reference['ordered'],(name,'replay stream')
  report['rollbacks']+=1;report['captures']+=1
  report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),'args':args,'output':wanted}
  print('PASS testbench_io',name,flush=True)
 ir=json.loads((out/'parallel/parallel.json').read_text());assert ir['parallel']['partitions']==2,ir['parallel']
 waves=timeline(*read(out/'parallel/parallel-settled.vcd'))
 for lane in ['u','v']:assert waves[('top',lane,'errors')][2][-1][1]==(0,0),lane
 for port in ['first','second']:assert waves[('top',port)][2][-1][1]==(127,0),port
 report['real_parallel_partitions']=2
 negatives={
  'test_count':('int r;initial r=$test$plusargs("a","b");','argument count'),
  'value_count':('int r;initial r=$value$plusargs("a=%d");','argument count'),
  'format_count':('string s;initial s=$sformatf();','syntax error'),
  'task_count':('string s;initial $sformat(s);','requires a target'),
  'net_target':('wire[31:0] n;int r;initial r=$value$plusargs("n=%d",n);','variable target'),
  'enum_target':('typedef enum int{A=0,B=1}e; e n;int r;initial r=$value$plusargs("n=%d",n);','enum target'),
  'const_target':('task automatic t(const ref int n);int r;r=$value$plusargs("n=%d",n);endtask int n;initial t(n);','const ref'),
  'const_format':('task automatic t(const ref string s);$sformat(s,"hello");endtask string s;initial t(s);','const ref'),
 }
 for name,(body,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text('module top;'+body+' endmodule\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  p=subprocess.run([str(compiler),str(source),'--emit-only','--emit-cpp',str(dest)],capture_output=True,text=True)
  (out/(name+'.stderr')).write_text(p.stderr)
  assert p.returncode==1 and diagnostic in p.stderr and not dest.exists(),(name,p.returncode,p.stdout,p.stderr)
 run([compiler,fixtures/'runtime_errors.sv','--emit-cpp',out/'runtime-errors.cpp','-o',out/'runtime-errors'],out,'runtime-errors-compile')
 runtime_errors=['unsupported string format','count mismatch','field width exceeds','one trailing','integral target','incomplete string format']
 for kind,diagnostic in enumerate(runtime_errors,1):
  p=subprocess.run([out/'runtime-errors','+error='+str(kind),'+n=3'],capture_output=True,text=True)
  (out/('runtime-error-'+str(kind)+'.stderr')).write_text(p.stderr)
  assert p.returncode==1 and diagnostic in p.stderr,(kind,p.returncode,p.stderr)
 report['runtime_rejections']=len(runtime_errors)
 # Unknown plusargs are accepted even without a plusarg-reading expression.
 assert '#define DSIM_PLUSARGS_ENABLED' not in (out/'format/plain.cpp').read_text()
 p=subprocess.run([out/'format/plain','--unknown-option'],capture_output=True,text=True)
 assert p.returncode==1 and 'usage:' in p.stderr,(p.returncode,p.stderr)
 report.update(status='PASS',negative_cases=len(negatives),unknown_native_option='REJECTED')
except Exception as error:report.update(status='FAIL',error=str(error));raise
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS testbench_io:',len(report['models']),'models,',report['captures'],'captures,',report['rollbacks'],'rollbacks')
