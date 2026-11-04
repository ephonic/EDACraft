"""Static type reflection and UVM string control/data operations, with VCS traces."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
compiler,out=map(lambda p:Path(p).resolve(),sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
fixtures=Path(__file__).resolve().parent;root=fixtures.parents[1]
sys.path.insert(0,str(root/'tests/waveform'))
from reader import read,declarations
expected=json.loads((fixtures/'expected.json').read_text())
report={'status':'RUNNING','models':{},'captures':0}
def run(args,work,label,success=True):
 p=subprocess.run(list(map(str,args)),cwd=work,capture_output=True,text=True,timeout=float(os.environ.get('DSIM_TEST_COMMAND_TIMEOUT','240')))
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==(0 if success else 1),(label,p.returncode,p.stderr[-5000:])
 return p.stdout

def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[i]) for key,(i,width,ranges) in declarations(meta).items()}
try:
 for name,wanted in expected.items():
  work=out/name;work.mkdir(exist_ok=True);reference=None
  source=fixtures/(name+'.sv');(work/'tb.sv').write_bytes(source.read_bytes())
  for backend,flags in [('serial',[]),('shared',['--shared-functions']),('wheel',['--shared-functions','--time-wheel'])]:
   run([compiler,*flags,work/'tb.sv','--wave-support','--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
   trace=run([work/backend,'--waveform',work/(backend+'.vcd'),'--wave-format','vcd','--wave-mode','ordered'],work,backend+'-run').splitlines()
   assert trace==wanted,(name,backend,trace,wanted)
   current=stream(work/(backend+'.vcd'));report['captures']+=1
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete ordered waveform')
  report['models'][name]={'status':'PASS','trace':wanted,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
  print('PASS reflection',name,flush=True)
 negatives={
  'empty':'module top;initial $display($typename());endmodule',
  'extra':'module top;initial $display($typename(1,2));endmodule',
  'type_value':'module top;typedef int T;int x;initial x=T;endmodule',
  'real_bits':'module top;initial $display($bits(real));endmodule',
  'real_range':'module top;initial $display($left(real));endmodule',
  'mixed_string_mux':'module top;string s;initial s=1?s:1;endmodule',
  'left_string_stream':'module top;string s,q[$];initial s={<<{q}};endmodule',
  'mixed_string_stream':'module top;string s,q[$];initial s={>>{q,8\'h41}};endmodule',
 }
 for name,source in negatives.items():
  work=out/('reject-'+name);work.mkdir(exist_ok=True);(work/'tb.sv').write_text(source);(work/'model.cpp').write_text('protected\n')
  run([compiler,'--shared-functions',work/'tb.sv','--emit-only','--emit-cpp',work/'model.cpp'],work,'compile',False)
  assert (work/'model.cpp').read_text()=='protected\n',name
 work=out/'reject-language';work.mkdir(exist_ok=True);(work/'tb.v').write_text('module top;reg x;initial $display($typename(x));endmodule\n');(work/'model.cpp').write_text('protected\n')
 run([compiler,'--language','verilog',work/'tb.v','--emit-only','--emit-cpp',work/'model.cpp'],work,'compile',False)
 assert '$typename requires SystemVerilog mode' in (work/'compile.stderr').read_text() and (work/'model.cpp').read_text()=='protected\n'
 report['negative_cases']=len(negatives)+1;report['status']='PASS'
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
