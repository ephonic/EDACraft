"""Integer string methods: complete streams, real partitions and checkpoint replay."""
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

expected=json.loads((fixtures/'expected.json').read_text())
report={'status':'RUNNING','models':{},'captures':0,'rollbacks':0}
try:
 for name,wanted in expected.items():
  work=out/name;work.mkdir(exist_ok=True);reference={}
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,fixtures/(name+'.sv'),*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-compile')
   for mode in ['ordered','settled']:
    wave=work/(backend+'-'+mode+'.vcd');wave.unlink(missing_ok=True)
    text=run([work/backend,'--waveform',wave,'--wave-format','vcd','--wave-mode',mode],work,backend+'-'+mode)
    assert text.splitlines()==wanted,(name,backend,mode,text,wanted)
    current=stream(wave)
    if backend=='serial':reference[mode]=current
    else:assert current==reference[mode],(name,backend,mode,'complete stream')
    report['captures']+=1
  # Exercise generated code with the string feature enabled and waveform code absent.
  run([compiler,fixtures/(name+'.sv'),'--emit-cpp',work/'plain.cpp','-o',work/'plain'],work,'plain-compile')
  assert run([work/'plain'],work,'plain-run').splitlines()==wanted,(name,'plain')
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  cutoff=1500 if name in ['mutation','lifetime'] else 500
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n',f'''
s.run_until({cutoff});
if(s.predict_until(10000,[](Sim&){{}},[](const Sim&){{return false;}},[](Sim&){{}}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
  run(['c++','-std=c++17','-O2','-pthread','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  wave=work/'replay.vcd';wave.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,'replay-run').splitlines()==wanted,(name,'replay output')
  assert stream(wave)==reference['ordered'],(name,'replay stream')
  report['rollbacks']+=1;report['captures']+=1
  report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),'output':wanted}
  print('PASS string_integer',name,flush=True)
 ir=json.loads((out/'parallel/parallel.json').read_text());assert ir['parallel']['partitions']==2,ir['parallel']
 for port in ['first','second']:assert timeline(*read(out/'parallel/parallel-settled.vcd'))[('top',port)][2][-1][1]==(0x2004,0),port
 for lane in ['u','v']:assert timeline(*read(out/'parallel/parallel-settled.vcd'))[('top',lane,'errors')][2][-1][1]==(0,0),lane
 report['real_parallel_partitions']=2
 negatives={
  'void_value':('string s;integer n;initial n=s.itoa(1);','void string method'),
  'putc_value':('string s;integer n;initial n=s.putc(0,65);','void string method'),
  'putc_count':('string s;initial s.putc(0);','argument count'),
  'parse_count':('string s;integer n;initial n=s.atoi(0);','argument count'),
  'format_count':('string s;initial s.hextoa();','argument count'),
  'putc_type':('string s,t;initial s.putc(t,65);','integral value'),
  'format_type':('string s,t;initial s.itoa(t);','integral value'),
  'const_putc':('task automatic f(const ref string s);s.putc(0,65);endtask string s;initial f(s);','const ref'),
  'const_format':('task automatic f(const ref string s);s.hextoa(123);endtask string s;initial f(s);','const ref'),
  'real_parse':('string s;initial s.atoreal();','unsupported string method'),
 }
 for name,(body,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text('module top;'+body+' endmodule\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  p=subprocess.run([str(compiler),str(source),'--emit-only','--emit-cpp',str(dest)],capture_output=True,text=True)
  (out/(name+'.stderr')).write_text(p.stderr)
  assert p.returncode==1 and diagnostic in p.stderr and not dest.exists(),(name,p.returncode,p.stdout,p.stderr)
 report.update(status='PASS',negative_cases=len(negatives))
except Exception as error:
 report.update(status='FAIL',error=str(error));raise
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS string_integer:',len(report['models']),'models,',report['captures'],'captures,',report['rollbacks'],'rollbacks')
