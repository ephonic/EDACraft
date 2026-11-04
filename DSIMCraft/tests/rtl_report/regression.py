"""Frozen Oct 24 RTL report: original applications and focused defect checks."""
import hashlib,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent;repo=root.parents[1];compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(repo/'tests/waveform'));from reader import read,declarations
expected=json.loads((root/'expected.json').read_text())
for name,digest in json.loads((root/'origin.json').read_text())['sha256'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
def run(command,work,label,ok=True):
 p=subprocess.run(list(map(str,command)),cwd=work,capture_output=True,text=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==(0 if ok else 1),(label,p.returncode,p.stdout,p.stderr)
 return p.stdout
def trace(text):return [x for x in text.splitlines() if x.startswith(('TRACE','p1 a=','p2 a=','p3 a='))]
def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
report={'status':'RUNNING','focused':{},'applications':{},'captures':0,'negative_cases':0}
try:
 for name,wanted in expected.items():
  work=out/name;work.mkdir(exist_ok=True);reference=None
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,root/'focused'/(name+'.sv'),*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
   wave=work/(backend+'.vcd');wave.unlink(missing_ok=True)
   text=run([work/backend,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,backend+'-run');assert trace(text)==wanted,(name,backend,text,wanted)
   current=stream(wave)
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete ordered streams')
   report['captures']+=1
  report['focused'][name]={'status':'PASS','source_sha256':hashlib.sha256((root/'focused'/(name+'.sv')).read_bytes()).hexdigest(),'trace':wanted}
  print('PASS RTL report focused',name,flush=True)
 markers={'fifo':'FIFO_TEST: ALL PASS','alu':'ALU_TEST: ALL PASS','uart':'UART_TEST: ALL PASS','fir':'FIR_TEST: PASS','cdc':'CDC_TEST: ALL PASS','svfeatures':'SV_TEST: ALL PASS'}
 for name,marker in markers.items():
  work=out/name;work.mkdir(exist_ok=True)
  run([compiler,root/name/'rtl.sv',root/name/'tb.sv','--emit-cpp',work/'model.cpp','-o',work/'model'],work,'compile')
  text=run([work/'model'],work,'run');assert marker in text and 'FAIL' not in text and 'ERRORS' not in text,(name,text)
  report['applications'][name]={'status':'PASS','stdout_sha256':hashlib.sha256(text.encode()).hexdigest()};print('PASS RTL report application',name,flush=True)
 negatives={
  'unknown_call':('module top;initial missing;endmodule','task/function is unknown'),
  'invalid_statement':('module top;initial 42;endmodule','expression statement requires'),
  'runtime_replication':("module top;integer n=2;logic[7:0]a;initial a={n{1'b1}};endmodule",'positive constant expression'),
  'hierarchy_write':('module leaf;logic a;endmodule module top;leaf dut();initial dut.a=1;endmodule','read-only'),
  'hierarchy_missing':('module leaf;logic a;endmodule module top;leaf dut();initial $display("%b",dut.missing);endmodule','unknown hierarchical member'),
  'ff_other_process':('module top;logic clk=0,q=0;always_ff @(posedge clk)q<=1;initial q=0;endmodule','another writer'),
  'var_net':('module top(input var wire a);endmodule','var port requires'),
 }
 for name,(source,diagnostic) in negatives.items():
  path=out/(name+'.sv');path.write_text(source+'\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  run([compiler,path,'--emit-only','--emit-cpp',dest],out,name,False)
  assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text());assert not dest.exists();report['negative_cases']+=1
 # var remains an ordinary identifier in Verilog mode.
 path=out/'var_identifier.v';path.write_text('module top;integer var=9;initial $display("TRACE var_identifier %0d",var);endmodule\n')
 run([compiler,path,'--language','verilog','-o',out/'var_identifier'],out,'var-identifier-compile')
 assert run([out/'var_identifier'],out,'var-identifier-run')=='TRACE var_identifier 9\n'
 report['status']='PASS'
except Exception as error:report.update(status='FAIL',error=str(error));raise
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS RTL report:',len(report['focused']),'focused models /',report['captures'],'captures,',len(report['applications']),'original applications,',report['negative_cases'],'rejects')
