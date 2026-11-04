"""Class formatting: same-source VCS traces, native-only contracts and complete waves."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
compiler,out=map(lambda p:Path(p).resolve(),sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
fixtures=Path(__file__).resolve().parent;root=fixtures.parents[1]
sys.path.insert(0,str(root/'tests/waveform'));from reader import read
expected=json.loads((fixtures/'expected.json').read_text());report=dict(status='RUNNING',models={},captures=0)
def run(args,w,label,ok=True):
 p=subprocess.run(list(map(str,args)),cwd=w,capture_output=True,text=True,timeout=float(os.getenv('DSIM_TEST_COMMAND_TIMEOUT','600')))
 (w/(label+'.stdout')).write_text(p.stdout);(w/(label+'.stderr')).write_text(p.stderr)
 assert (p.returncode==0)==ok and p.returncode>=0,(label,p.returncode,p.stderr[-4000:]);return p
try:
 cases=[(name,fixtures/(name+'.sv'),wanted) for name,wanted in expected.items()]
 cases += [('native-'+name,fixtures/'native-only'/(name+'.sv'),wanted) for name,wanted in json.loads((fixtures/'native-only/expected.json').read_text()).items()]
 for name,source,wanted in cases:
  w=out/name;w.mkdir(exist_ok=True);reference=None
  for backend,flags in [('serial',[]),('shared',['--shared-functions']),('wheel',['--shared-functions','--time-wheel'])]:
   run([compiler,*flags,source,'--wave-support','--emit-cpp',w/(backend+'.cpp'),'-o',w/backend],w,backend+'-compile')
   trace=run([w/backend,'--waveform',w/(backend+'.vcd'),'--wave-format','vcd','--wave-mode','ordered'],w,backend+'-run').stdout.splitlines()
   assert trace==wanted,(name,backend,trace,wanted)
   current=read(w/(backend+'.vcd'));report['captures']+=1
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete waveform')
  report['models'][name]=dict(trace=wanted,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
  print('PASS object formatting',name,flush=True)
 negatives={
  'implicit':('class Item;int n;endclass module top;string s;Item item;always_comb $swrite(s,item);endmodule','class formatting in implicit sensitivity'),
  'star':('class Item;int n;endclass module top;string s;Item item;always @* $swrite(s,item);endmodule','class formatting in implicit sensitivity'),
 }
 for name,(source,message) in negatives.items():
  w=out/('reject-'+name);w.mkdir(exist_ok=True);(w/'tb.sv').write_text(source);(w/'model.cpp').write_text('protected\n')
  p=run([compiler,w/'tb.sv','--emit-only','--emit-cpp',w/'model.cpp'],w,'compile',False)
  assert message in p.stderr,(name,p.stderr)
  assert (w/'model.cpp').read_text()=='protected\n'
 runtime={
  'numeric':('class Item;int value;endclass module top;Item item;string s;initial begin item=new();$swrite(s,"%d",item);end endmodule','class formatting currently requires %p'),
  'nonclass':('module top;string s;initial s=$sformatf("%p",3);endmodule','%p output currently requires a class value'),
  'field':('class Item;static int values[2];endclass module top;Item item;string s;initial begin item=new();$swrite(s,item);end endmodule','class output field type is not supported yet'),
 }
 for name,(source,message) in runtime.items():
  w=out/('runtime-'+name);w.mkdir(exist_ok=True);(w/'tb.sv').write_text(source)
  run([compiler,w/'tb.sv','-o',w/'native'],w,'compile');p=run([w/'native'],w,'run',False)
  assert message in p.stderr,(name,p.stderr)
 report.update(status='PASS',negative_cases=len(negatives),runtime_rejections=len(runtime))
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
