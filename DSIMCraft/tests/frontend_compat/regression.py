"""Reported parser gaps: execute, inspect waves, and reject invalid designs."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=Path(__file__).resolve().parent;expected=json.loads((fixtures/'expected.json').read_text())
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
 source=fixtures/(name+('.v' if name in ['keyword_names','legacy_function'] else '.sv'))
 language=['--language','verilog'] if name in ['ref_identifier','keyword_names','legacy_function'] else []
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
  if backend=='parallel' and name=='packed_parallel':
   run([work/backend,'--parallel-stats'],work,'parallel-stats')
   assert '"partitions":2' in (work/'parallel-stats.stderr').read_text()
 if name=='packed_parallel':
  state=timeline(*read(work/'serial-settled.vcd'))
  for port in ['one','two']:assert state[('top',port)][2][-1][1]==(0x1203,0)
 if name in ['packed_runtime','packed_formals','packed_parallel']:
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
 print('PASS frontend',name,flush=True)

negative={
 'ambiguous':('module a;endmodule module b;endmodule','multiple top modules'),
 'no_root':('module a;b u();endmodule module b;a u();endmodule','cannot infer a top module'),
 'runtime_bound':('module top;integer n;logic[n:0][7:0] a;initial begin end endmodule','packed dimensions require two constant bounds'),
 'unknown_bound':("module top;logic[1'bx:0][7:0] a;initial begin end endmodule",'packed dimension bound is unknown'),
 'oversize':('module top;logic[1048575:0][7:0] a;initial begin end endmodule','packed dimensions exceed'),
 'direction':('module top;logic[1:0][7:0] a;initial a[0:1]=0;endmodule','packed part-select direction'),
 'excess_index':('module top;logic[1:0][7:0] a;initial a[0][0][0]=0;endmodule','too many packed indices'),
 'sv_ref':('module top;integer ref;initial ref=1;endmodule','syntax error'),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text(source+'\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
 run([compiler,path,'--emit-only','--emit-cpp',dest],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text())
 assert not dest.exists(),name
# Explicit root override and legacy root preference remain deterministic.
for name,body,flags,wanted in [
 ('override','module a;initial $display("TRACE selected a");endmodule module b;initial $display("TRACE selected b");endmodule',['--top','b'],'TRACE selected b'),
 ('legacy','module ignored;initial $display("TRACE ignored");endmodule module top;initial $display("TRACE selected top");endmodule',[],'TRACE selected top'),
]:
 path=out/(name+'.sv');path.write_text(body+'\n')
 run([compiler,path,*flags,'-o',out/name],out,name+'-compile')
 assert run([out/name],out,name+'-run').splitlines()==[wanted]
report.update(status='PASS',negative_cases=len(negative),root_selection_cases=2,real_parallel_partitions=2)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS frontend compatibility',report['captures'],'captures and',report['rollbacks'],'rollbacks')
