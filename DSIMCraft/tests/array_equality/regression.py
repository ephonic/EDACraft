"""VCS aggregate equality semantics and bounded default function expansion."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
compiler,out=map(lambda p:Path(p).resolve(),sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
fixtures=Path(__file__).resolve().parent;root=fixtures.parents[1]
sys.path.insert(0,str(root/'tests/waveform'))
from reader import read,declarations
expected=json.loads((fixtures/'expected.json').read_text())
report={'status':'RUNNING','models':{},'captures':0}
config={s.split('=',1)[0].split(':',1)[0]:s.split('=',1)[1] for s in (compiler.parent/'CMakeCache.txt').read_text().splitlines() if '=' in s and not s.startswith('//')}
def run(args,work,label,success=True):
 p=subprocess.run(list(map(str,args)),cwd=work,capture_output=True,text=True,timeout=float(os.environ.get('DSIM_TEST_COMMAND_TIMEOUT','240')))
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==(0 if success else 1),(label,p.returncode,p.stderr[-5000:])
 return p

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
   trace=run([work/backend,'--waveform',work/(backend+'.vcd'),'--wave-format','vcd','--wave-mode','ordered'],work,backend+'-run').stdout.splitlines()
   assert trace==wanted,(name,backend,trace,wanted)
   current=stream(work/(backend+'.vcd'));report['captures']+=1
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete ordered waveform')
  if name=='effects':
   code=(work/'shared.cpp').read_text();assert code.count('\ns.run();\n')==1
   (work/'replay.cpp').write_text(code.replace('\ns.run();\n','\ns.run_until(0);\nif(s.predict_until(10,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("unexpected commit");\nif(s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing rollback");\ns.run();\n'))
   strict=['-fp-model=strict'] if Path(config['DSIM_MODEL_CXX']).name in ('icpx','icpc') else []
   run([config['DSIM_MODEL_CXX'],'-std=c++17','-O2','-pthread',*strict,'-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
   trace=run([work/'replay','--waveform',work/'replay.vcd','--wave-format','vcd','--wave-mode','ordered'],work,'replay-run').stdout.splitlines()
   assert trace==wanted and stream(work/'replay.vcd')==reference
   report['captures']+=1;report['rollbacks']=1
  report['models'][name]={'status':'PASS','trace':wanted,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
  print('PASS equality',name,flush=True)
 negatives={
  'mixed_kind':'module top;int a[$],b[];initial $display(a===b);endmodule',
  'mixed_state':'module top;bit a[$];logic b[$];initial $display(a===b);endmodule',
  'mixed_element':'module top;int a[$];string b[$];initial $display(a===b);endmodule',
  'real':'module top;real a[2],b[2];initial $display(a==b);endmodule',
  'scalar':'module top;int a[$],b;initial $display(a===b);endmodule',
  'math':'module top;int a[$],b[$];initial $display(a+b);endmodule',
  'ordering':'module top;int a[$],b[$];initial $display(a<b);endmodule',
  'fixed_shape':'module top;int a[2][3],b[3][2];initial $display(a===b);endmodule',
  'fixed_size':'module top;int a[2],b[3];initial $display(a===b);endmodule',
  'associative':'module top;int a[int],b[int];initial $display(a===b);endmodule',
  'pending_nba':'module top;int a[$],b[$],x;initial x<=@(a==b) 1;endmodule',
  'swrite_without_format':'module top;string s;initial $swrite(s,42);endmodule',
  'shorthand_replication':"module top;wire [6:0] a={7{1{1'b1}}};endmodule",
 }
 for name,source in negatives.items():
  source=source.replace('$display(', '$display("%b",')
  work=out/('reject-'+name);work.mkdir(exist_ok=True);(work/'tb.sv').write_text(source);(work/'model.cpp').write_text('protected\n')
  rejected=run([compiler,work/'tb.sv','--emit-only','--emit-cpp',work/'model.cpp'],work,'compile',False)
  required={
   'mixed_kind':'matching container kinds','mixed_state':'equivalent element types',
   'mixed_element':'equivalent element types','real':'real array equality is not supported yet',
   'scalar':'two unpacked array values','math':'equality operators only','ordering':'equality operators only',
   'fixed_shape':'matching unpacked dimensions','fixed_size':'matching unpacked dimensions',
   'associative':'associative arrays require matching key types',
   'pending_nba':'array equality in pending NBA event controls is not supported yet',
   'swrite_without_format':'explicit string format','shorthand_replication':'syntax error',
  }[name]
  assert required in rejected.stderr,(name,rejected.stderr)
  assert (work/'model.cpp').read_text()=='protected\n',name
 # Exponential call graph is a language-independent trigger for the automatic
 # fallback, rather than recognizing UVM names or changing library source.
 work=out/'budget';work.mkdir(exist_ok=True)
 functions=['function automatic int f0(int n);return 1;endfunction']
 for i in range(1,26):functions.append(f'function automatic int f{i}(int n);if(n==0)return {i};return f{i-1}(n-1)+f{i-1}(n-1);endfunction')
 (work/'tb.sv').write_text('module top;\n'+'\n'.join(functions)+'\ninitial $display("TRACE budget %0d",f25(2));endmodule\n')
 default=run([compiler,work/'tb.sv','--emit-cpp',work/'default.cpp','-o',work/'default'],work,'default-compile')
 assert 'using shared function bodies' in default.stderr,default.stderr
 run([compiler,'--shared-functions',work/'tb.sv','--emit-only','--emit-cpp',work/'shared.cpp'],work,'shared-compile')
 assert (work/'default.cpp').read_bytes()==(work/'shared.cpp').read_bytes()
 assert (work/'default.cpp').stat().st_size<2_000_000
 assert run([work/'default'],work,'default-run').stdout.splitlines()==['TRACE budget 92']
 report['budget']={'status':'PASS','cpp_bytes':(work/'default.cpp').stat().st_size}
 report['negative_cases']=len(negatives);report['status']='PASS'
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
