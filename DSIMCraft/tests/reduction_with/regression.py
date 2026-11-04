"""Unpacked array reduction with: widths, storage, timing, frames and replay."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=Path(__file__).resolve().parent;expected=json.loads((fixtures/'expected.json').read_text());expected['shadowed_select']=expected['values']

config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in (compiler.parent/'CMakeCache.txt').read_text().splitlines() if '=' in x and not x.startswith('//')}
def run(command,work,label,ok=True):
 p=subprocess.run(list(map(str,command)),cwd=work,text=True,capture_output=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode>=0 and (p.returncode==0)==ok,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout
def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
report={'status':'RUNNING','models':{},'captures':0,'rollbacks':0}
for name,wanted in expected.items():
 work=out/name;work.mkdir(exist_ok=True);references={}
 source=(fixtures/'native-only' if name=='shadowed_select' else fixtures)/(name+'.sv')
 language=[]
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,source,*language,*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-compile')
  trace=run([work/backend],work,backend+'-run');assert [line for line in trace.splitlines() if line.startswith('TRACE')]==wanted,(name,backend,trace,wanted)
  for mode in ['ordered','settled']:
   for fmt in ['vcd','dwf']:
    wave=work/(backend+'-'+mode+'.'+fmt)
    wave.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',wave,'--wave-mode',mode,'--wave-format',fmt],work,backend+'-'+mode+'-'+fmt)==trace
    state=streams(wave);report['captures']+=1
    if backend=='serial' and fmt=='vcd':references[mode]=state
    assert state==references[mode],(name,backend,mode,fmt)
  if backend=='parallel' and name=='parallel':
   run([work/backend,'--parallel-stats'],work,'parallel-stats')
   assert '"partitions":2' in (work/'parallel-stats.stderr').read_text()
 if name=='parallel':
  state=timeline(*read(work/'serial-settled.vcd'))
  for port in ['one','two']:assert state[('top',port)][2][-1][1]==(0x7703,0)
 if name in ['timing','automatic','dynamic']:
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
s.run_until(1000);
if(s.predict_until(30000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
  run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  (work/'replay.dwf').unlink(missing_ok=True)
  assert run([work/'replay','--waveform',work/'replay.dwf','--wave-mode','ordered'],work,'replay-run')==(work/'serial-run.stdout').read_text()
  assert streams(work/'replay.dwf')==references['ordered'];report['rollbacks']+=1;report['captures']+=1
 report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'trace':wanted}
 print('PASS array reduction with',name,flush=True)

negative={
 'receiver':("integer a,out;initial out=a.sum with(item);",'with clause requires'),
 'nonmethod':("integer a,out;initial out=a with(item);",'with clause requires an array method'),
 'method':("integer a[],out;initial out=a.size() with(item);",'with clause requires'),
 'rank':("integer a[2][2],out;initial out=a.sum with(item);",'with clause requires'),
 'arguments':("integer a[2],out;initial out=a.sum(x,y) with(x+y);",'iterator argument must be one identifier'),
 'argument_expression':("integer a[2],out;initial out=a.sum(1) with(item);",'iterator argument must be one identifier'),
 'leak':("integer a[2],out;initial begin out=a.sum with(item);out=item;end",'parse/semantic analysis failed'),
 'readonly':("integer a[2],out;initial out=a.sum with(item++);",'iterator is read-only'),
 'external_write':("integer a[2],out,bias=0;initial out=a.sum with(item+bias++);",'requires no user calls or side effects'),
 'function_call':("function automatic integer f(input integer x);return x;endfunction integer a[2],out;initial out=a.sum with(f(1)+item);",'requires no user calls or side effects'),
 'prefix':("integer a[2][2],i=0,out;initial out=a[i].sum with(item);",'requires static subarray indices'),
 'enum':("typedef enum logic[7:0]{A=1,B=2} t;t a[2];integer out;initial out=a.sum;",'array reduction enum, class and aggregate elements'),
 'multiselect':("logic[1:0][3:0] a[2];integer out;initial out=a.sum with(item[0]);",'one-dimensional packed selects'),
 'duplicate':("integer a[2],out;initial out=a.sum with(item) with(item);",'duplicate array with clause'),
}

for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module top;'+source+' endmodule\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
 run([compiler,path,'--emit-only','--emit-cpp',dest],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text())
 assert not dest.exists(),name
path=out/'verilog-mode.v';path.write_text("module top;integer a[2],out;initial out=a.sum with(item);endmodule\n")
run([compiler,path,'--language','verilog','--emit-only','--emit-cpp',out/'verilog-mode.cpp'],out,'verilog-mode',False)
assert 'syntax' in (out/'verilog-mode.stderr').read_text()
path=out/'keyword.v';path.write_text('module top;integer with=7;initial $display("TRACE keyword %0d",with);endmodule\n')
run([compiler,path,'--language','verilog','-o',out/'keyword'],out,'keyword-compile')
assert run([out/'keyword'],out,'keyword-run')=='TRACE keyword 7\n'
# Check the parallel backend really scheduled independent worker partitions.
parallel_ir=json.loads((out/'parallel/parallel.json').read_text())
assert parallel_ir['parallel']['partitions']==2
report.update(status='PASS',negative_cases=len(negative)+1,real_parallel_partitions=2)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS array reduction with compatibility',report['captures'],'captures and',report['rollbacks'],'rollbacks')
