"""Original complex REPORT fixtures and boundary checks for its missing features."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations
cache_path=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
cache={line.split('=',1)[0].split(':',1)[0]:line.split('=',1)[1] for line in cache_path.read_text().splitlines() if '=' in line and not line.startswith('//')}
def run(args,work,label,expected=0):
 p=subprocess.run(list(map(str,args)),cwd=work,text=True,capture_output=True,timeout=240)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==expected,(label,p.returncode,p.stdout,p.stderr)
 assert '[DEBUG]' not in p.stdout+p.stderr and 'unknown err.' not in p.stderr,(label,'opaque diagnostic')
 return p.stdout

def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for time,kind,data in events:
  if kind=='value':values[data[0]].append((time,data[1]))
 return {key:(width,ranges,values[i]) for key,(i,width,ranges) in declarations(meta).items()}
expected=json.loads((fixtures/'expected.json').read_text())
report={'status':'RUNNING','probes':{},'designs':{},'extended':{},'captures':0,'rollbacks':0,'negative_cases':0}
try:
 for source in sorted((fixtures/'probes').glob('p*.sv')):
  work=out/'probes'/source.stem;work.mkdir(parents=True,exist_ok=True);shutil.copy2(fixtures/'probes/mem.hex',work/'mem.hex')
  run([compiler,'--top','tb',source,'-o',work/'simv'],work,'compile')
  text=run([work/'simv'],work,'run');assert text.splitlines()==expected['probes'][source.stem],(source,text)
  report['probes'][source.stem]={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'stdout':text,'status':'PASS'}
  print('PASS complex probe',source.stem,flush=True)
 for name in ['rv32i','axil','arbiter','muldiv','crc32','svstress']:
  work=out/'designs'/name;work.mkdir(parents=True,exist_ok=True)
  for source in (fixtures/name).iterdir():
   if source.is_file():shutil.copy2(source,work/source.name)
  run([compiler,'--top','tb','rtl.sv','tb.sv','-o',work/'simv'],work,'compile')
  text=run([work/'simv'],work,'run');assert 'ALL PASS' in text and 'FAIL' not in text and 'MISMATCH' not in text,(name,text)
  report['designs'][name]={'status':'PASS','stdout':text};print('PASS complex design',name,flush=True)
 for name,wanted in expected['extended'].items():
  source=fixtures/'extended'/(name+'.sv');work=out/'extended'/name;work.mkdir(parents=True,exist_ok=True);reference=None
  def clean_memory():
   for file in ['wide.hex','wide.bin','partial.hex']:(work/file).unlink(missing_ok=True)
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,source,'--top','tb',*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
   wave=work/(backend+'.vcd');wave.unlink(missing_ok=True);clean_memory()
   text=run([work/backend,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,backend+'-run')
   assert text.splitlines()==wanted,(name,backend,text,wanted)
   current=stream(wave)
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete ordered timeline')
   report['captures']+=1
  if name in ['force_values','procedural_samples','memory_files']:
   code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
   check='if(std::ifstream("wide.hex"))throw std::runtime_error("speculative file write escaped");' if name=='memory_files' else ''
   (work/'replay.cpp').write_text(code.replace('\ns.run();\n',f'''
s.run_until(1000);
if(s.predict_until(35000,[](Sim&){{}},[](const Sim&){{{check}return false;}},[](Sim&){{{check}}}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
   run(['c++','-std=c++17','-O2','-pthread','-I'+cache['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',cache['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
   wave=work/'replay.vcd';wave.unlink(missing_ok=True);clean_memory()
   text=run([work/'replay','--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,'replay-run')
   assert text.splitlines()==wanted and stream(wave)==reference,(name,'rollback output/wave')
   report['captures']+=1;report['rollbacks']+=1
  report['extended'][name]={'status':'PASS','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'stdout':wanted};print('PASS complex boundary',name,flush=True)
 negatives={
  'ansi_input':('module tb(input wire a);wire a;endmodule','redefined'),
  'ansi_output':('module tb(output reg q);reg q;endmodule','redefined'),
  'duplicate_reg':('module tb;reg a;reg a;endmodule','redefined'),
  'duplicate_init':('module tb;reg a=0;reg a=1;endmodule','redefined'),
  'duplicate_split':('module tb(q);output q;reg q;reg q;endmodule','redefined'),
  'split_width':('module tb(q);output[7:0]q;reg[3:0]q;endmodule','redefined'),
  'clockless':('module tb;reg a;initial $display("%b",$past(a));endmodule','procedural clock'),
  'ambiguous_clock':('module tb;reg a,b,c;always @(posedge a or negedge b)c=$past(c);endmodule','procedural clock'),
  'constant_external':('module tb;integer n=3;function integer f(input integer a);f=n+a;endfunction localparam P=f(2);endmodule','constant'),
  'constant_write':('module tb;integer n;function integer f(input integer a);begin n=a;f=a;end endfunction localparam P=f(2);endmodule','constant'),
  'static_recursion':('module tb;function integer f(input integer n);if(n<1)f=1;else f=n*f(n-1);endfunction integer a;initial a=f(4);endmodule','automatic scalar'),
  'force_part':('module tb;reg[7:0]v;initial force v[3:0]=0;endmodule','whole static signal'),
  'force_effect':('module tb;reg v;integer a;initial force v=a++;endmodule','pure integral'),
  'struct_arithmetic':('module tb;typedef struct{logic[7:0]a;}t;t s;integer r;initial r=s+1;endmodule','unpacked structs'),
  'struct_cast':("module tb;typedef struct{logic[7:0]a;}t;t s;integer r;initial r=int'(s);endmodule",'unpacked structs'),
  'struct_assignment':('module tb;typedef struct{logic[7:0]a;}t;t s;initial s=1;endmodule','same struct type'),
 }
 for name,(text,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text(text+'\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  run([compiler,'--top','tb',source,'--emit-only','--emit-cpp',dest],out,name,1)
  assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text());assert not dest.exists(),name
  report['negative_cases']+=1
 # Exhausting a finite budget must not claim that a loop was proven.
 work=out/'budget';work.mkdir(exist_ok=True);(work/'input.sv').write_text('module tb;initial forever begin end endmodule\n')
 run([compiler,work/'input.sv','-o',work/'simv'],work,'compile');run([work/'simv','--max-events','20'],work,'run',1)
 assert 'execution budget exhausted' in (work/'run.stderr').read_text()
 report['status']='PASS'
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS complex report:',len(report['probes']),'probes,',len(report['designs']),'designs,',report['captures'],'captures,',report['rollbacks'],'rollbacks,',report['negative_cases'],'rejections',flush=True)
