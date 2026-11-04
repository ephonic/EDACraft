"""String signatures, copy/ref semantics, activation lifetimes and rollback."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations,timeline
cache=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
def run(command,work,label,ok=True):
 p=subprocess.run(list(map(str,command)),cwd=work,capture_output=True,text=True,timeout=240)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==(0 if ok else 1),(label,p.returncode,p.stdout,p.stderr)
 return p.stdout
def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
expected=json.loads((fixtures/'expected.json').read_text())
report={'status':'RUNNING','models':{},'captures':0,'rollbacks':0}
try:
 for name,wanted in expected.items():
  work=out/name;work.mkdir(exist_ok=True);references={}
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,fixtures/(name+'.sv'),*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-compile')
   for mode in ['ordered','settled']:
    wave=work/(backend+'-'+mode+'.vcd');wave.unlink(missing_ok=True)
    text=run([work/backend,'--waveform',wave,'--wave-format','vcd','--wave-mode',mode],work,backend+'-'+mode)
    assert text.splitlines()==wanted,(name,backend,mode,text,wanted)
    current=streams(wave)
    if backend=='serial':references[mode]=current
    else:assert current==references[mode],(name,backend,mode,'complete signal streams')
    report['captures']+=1
  if name in ['automatic','events','lifetime','references']:
   code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
   (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
s.run_until(2000);
if(s.predict_until(30000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
   run(['c++','-std=c++17','-O2','-pthread','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
   wave=work/'replay.vcd';wave.unlink(missing_ok=True)
   assert run([work/'replay','--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,'replay-run').splitlines()==wanted
   assert streams(wave)==references['ordered'],(name,'rollback full stream');report['captures']+=1;report['rollbacks']+=1
  report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),'trace':wanted}
  print('PASS string subroutines',name,flush=True)
 ir=json.loads((out/'parallel/parallel.json').read_text());assert ir['parallel']['partitions']==2,ir['parallel']
 for signal in ['first','second']:assert timeline(*read(out/'parallel/parallel-settled.vcd'))[('top',signal)][2][-1][1]==(4,0),signal
 for lane in ['u','v']:assert timeline(*read(out/'parallel/parallel-settled.vcd'))[('top',lane,'errors')][2][-1][1]==(0,0),lane
 negatives={
  'ref_numeric':('logic x;task automatic f(ref string s);begin end endtask initial f(x);','equivalent argument types'),
  'ref_string':('string x;task automatic f(ref logic s);begin end endtask initial f(x);','equivalent argument types'),
  'ref_literal':('task automatic f(ref string s);begin end endtask initial f("text");','whole variable'),
  'const_write':('string x;task automatic f(const ref string s);s="bad";endtask initial f(x);','const ref'),
  'const_forward':('string x;task automatic g(ref string s);s="bad";endtask task automatic f(const ref string s);g(s);begin end endtask initial f(x);','const ref'),
  'static_ref':('string x;task f(ref string s);begin end endtask initial f(x);','automatic subroutine'),
  'array':('string x;task automatic f(input string s[2]);begin end endtask initial f(x);','array copy requires matching unpacked array'),
  'return_real':('string x;function automatic real f();return x;endfunction real n;initial n=f();','real conversion requires a numeric value'),
  'argument_real':('function automatic real f(input real v);return v;endfunction function automatic string g();return "text";endfunction real n;initial n=f(g());','real conversion requires a numeric value'),
  'result_real':('function automatic string f();return "text";endfunction real n;initial n=f();','real conversion requires a numeric value'),
 }
 for name,(body,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text('module top;'+body+'endmodule\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  run([compiler,source,'--emit-only','--emit-cpp',dest],out,name,False)
  assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text());assert not dest.exists(),name
 report.update(status='PASS',negative_cases=len(negatives),real_parallel_partitions=2)
except Exception as error:
 report.update(status='FAIL',error=str(error));raise
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS string subroutines:',report['captures'],'captures,',report['rollbacks'],'rollbacks,',report['negative_cases'],'rejections')
