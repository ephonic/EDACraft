"""Interface shared storage, modport checks, backends, rollback and partitioning."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations,timeline
cache_path=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
cache={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache_path.read_text().splitlines() if '=' in x and not x.startswith('//')}
def run(cmd,work,label,ok=True):
 p=subprocess.run(list(map(str,cmd)),cwd=work,text=True,capture_output=True,timeout=240)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==(0 if ok else 1),(label,p.returncode,p.stdout,p.stderr)
 return p.stdout
def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
expected=json.loads((fixtures/'expected.json').read_text());report={'status':'RUNNING','models':{},'captures':0,'rollbacks':0}
try:
 for name,wanted in expected.items():
  work=out/name;work.mkdir(exist_ok=True);reference=None
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,fixtures/(name+'.sv'),*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-compile')
   wave=work/(backend+'.vcd');wave.unlink(missing_ok=True)
   text=run([work/backend,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,backend+'-run')
   assert [x for x in text.splitlines() if x.startswith(('TRACE','D4 INTERFACE'))]==wanted,(name,backend,text,wanted)
   assert 'FAIL' not in text,(name,backend,text)
   current=stream(wave)
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete ordered stream')
   report['captures']+=1
  if name in ['forwarding','aggregates','parameterized','nets']:
   cutoff=100
   code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
   (work/'replay.cpp').write_text(code.replace('\ns.run();\n',f'''
s.run_until({cutoff});
if(s.predict_until(10000,[](Sim&){{}},[](const Sim&){{return false;}},[](Sim&){{}}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
   run(['c++','-std=c++17','-O2','-pthread','-I'+cache['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',cache['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
   wave=work/'replay.vcd';wave.unlink(missing_ok=True)
   assert run([work/'replay','--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,'replay-run')==(work/'serial-run.stdout').read_text()
   assert stream(wave)==reference,(name,'rollback full ordered stream');report['rollbacks']+=1;report['captures']+=1
  report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),'trace':wanted}
  if name=='ordinary_hierarchy':
   values=timeline(*read(work/'serial.vcd'))
   assert values[('top','x','value')][2]==[(0,(0,0)),(1,(7,0)),(3,(9,0))],values
   assert values[('top','observed')][2][-2:]==[(2,(7,0)),(4,(9,0))],values
  print('PASS interfaces',name,flush=True)
 ir=json.loads((out/'parallel/parallel.json').read_text());assert ir['parallel']['partitions']==2,ir['parallel']
 for port in ['one','two']:assert timeline(*read(out/'parallel/parallel.vcd'))[('top',port)][2][-1][1]==(19,0),port
 assert json.loads((out/'report/parallel.json').read_text())['parallel']['partitions']==1,'shared interface must stay together'
 iface='interface bus_if;logic[7:0] value;logic hidden;modport ro(input value);modport rw(output value);endinterface '
 negatives={
  'instance_array':(iface+'module top;bus_if x[1:0]();endmodule','interface instance arrays'),
  'ordinary_port':(iface+'module c(input logic b);endmodule module top;bus_if x();c u(x);endmodule','unsupported primary'),
  'clock_not_visible':('interface bus_if(input logic clk);logic value;modport rw(output value);endinterface module c(bus_if.rw b);always @(posedge b.clk)b.value<=1;endmodule module top;logic clk;bus_if x(clk);c u(x);endmodule','not visible via modport'),
  'write_input':(iface+'module c(bus_if.ro b);initial b.value=1;endmodule module top;bus_if x();c u(x);endmodule','cannot write input'),
  'write_input_select':(iface+'module c(bus_if.ro b);initial b.value[3:0]=1;endmodule module top;bus_if x();c u(x);endmodule','cannot write input'),
  'hidden_member':(iface+'module c(bus_if.ro b);initial $display("%h",b.hidden);endmodule module top;bus_if x();c u(x);endmodule','not visible via modport'),
  'unknown_view':(iface+'module c(bus_if.missing b);endmodule module top;bus_if x();c u(x);endmodule','unknown modport'),
  'incompatible_view':(iface+'module c(bus_if.rw b);endmodule module top;bus_if x();c u(x.ro);endmodule','incompatible modport'),
  'wrong_type':(iface+'interface other;logic value;endinterface module c(bus_if b);endmodule module top;other x();c u(x);endmodule','interface type mismatch'),
  'number_actual':(iface+'module c(bus_if b);endmodule module top;c u(1);endmodule','requires an elaborated interface'),
  'module_actual':(iface+'module leaf;endmodule module c(bus_if b);endmodule module top;leaf x();c u(x);endmodule','requires an elaborated interface'),
  'unconnected':(iface+'module c(bus_if b);endmodule module top;c u();endmodule','requires an elaborated interface'),
  'explicit_empty':(iface+'module c(bus_if b);endmodule module top;c u(.b());endmodule','requires an elaborated interface'),
  'duplicate_connection':(iface+'module c(bus_if b);endmodule module top;bus_if x();c u(.b(x),.b(x));endmodule','duplicate module port'),
  'bad_member':('interface bus_if;logic value;modport ro(input missing);endinterface module top;bus_if x();endmodule','unknown signal'),
  'duplicate_member':('interface bus_if;logic value;modport ro(input value,value);endinterface module top;bus_if x();endmodule','duplicate modport member'),
  'duplicate_view':('interface bus_if;logic value;modport ro(input value);modport ro(input value);endinterface module top;bus_if x();endmodule','duplicate modport'),
  'outside_interface':('module top;logic value;modport ro(input value);endmodule','requires an interface'),
  'numeric_formal':(iface+'module c(bus_if b);initial $display("%h",b);endmodule module top;bus_if x();c u(x);endmodule','namespace'),
 }
 for name,(text,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text(text+'\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  run([compiler,source,'--emit-only','--emit-cpp',dest],out,name,False)
  assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text());assert not dest.exists(),name
 report.update(status='PASS',negative_cases=len(negatives),real_parallel_partitions=2)
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS interfaces:',report['captures'],'captures,',report['rollbacks'],'rollbacks,',report['negative_cases'],'rejections')
