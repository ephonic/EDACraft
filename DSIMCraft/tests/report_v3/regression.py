"""Report v3 composition: hierarchical elements, enum metadata, package storage and text VCD."""
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
   assert [x for x in text.splitlines() if x.startswith(('TRACE','H_ARR','H_DEEP','D3 CONC_ASSERT'))]==wanted,(name,backend,text,wanted)
   assert 'FAIL' not in text,(name,backend,text)
   current=stream(wave)
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete ordered stream')
   report['captures']+=1
  if name in ['hierarchy','package_state','package_arrays','report_property']:
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
  print('PASS report-v3',name,flush=True)
 ir=json.loads((out/'parallel/parallel.json').read_text());assert ir['parallel']['partitions']==2,ir['parallel']
 for port in ['one','two']:assert timeline(*read(out/'parallel/parallel.vcd'))[('top',port)][2][-1][1]==(19,0),port
 assert json.loads((out/'package_state/parallel.json').read_text())['parallel']['partitions']==1,'shared package state must stay together'
 negatives={
  'package_net':('package p;wire a;endpackage module top;endmodule','cannot be nets'),
  'package_port':('package p;input logic a;endpackage module top;endmodule','module ports'),
  'hierarchy_write':('module leaf;reg[7:0] a[0:1];endmodule module top;leaf u();initial u.a[0]=1;endmodule','read-only'),
  'hierarchy_subarray':('module leaf;reg[7:0] a[0:1][0:1];endmodule module top;leaf u();initial $display("%h",u.a[0]);endmodule','all unpacked'),
  'hierarchy_method':('module leaf;reg[7:0] a[0:1];endmodule module top;leaf u();initial $display("%h",u.a[0].name());endmodule','enum'),
  'hierarchy_enum_args':('module leaf;typedef enum{A,B} t;t a;endmodule module top;leaf u();initial $display("%s",u.a.name(1));endmodule','too many arguments'),
  'package_automatic':('package p;automatic int a;endpackage module top;endmodule','syntax error'),
  'package_process':('package p;initial begin end endpackage module top;endmodule','unsupported package item'),
  'package_hidden':('package p;int a;endpackage module top;initial a=1;endmodule',''),
  'package_missing':('package p;int a;endpackage module top;initial p::missing=1;endmodule','package member'),
 }
 for name,(text,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text(text+'\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  run([compiler,source,'--emit-only','--emit-cpp',dest],out,name,False)
  assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text());assert not dest.exists(),name
 # Extension inference is shared by serial, wheel and merged parallel capture.
 for model in ['hierarchy','parallel']:
  for backend in ['serial','wheel','parallel']:
   work=out/model;exe=work/backend
   reference=stream(work/(backend+'.vcd'))
   for label,extension,flags,kind in [
    ('auto-vcd','.vcd',[],'vcd'),('auto-dwf','.dwf',[],'dwf'),
    ('format-first','.dwf',['--wave-format','vcd'],'vcd'),
    ('format-last','.vcd',['--wave-format','dwf'],'dwf')]:
    path=work/(backend+'-'+label+extension);path.unlink(missing_ok=True)
    args=[exe,*flags,'--waveform',path,'--wave-mode','ordered'] if label=='format-first' else [exe,'--waveform',path,'--wave-mode','ordered',*flags]
    run(args,work,backend+'-'+label)
    assert path.read_bytes().startswith(b'DWF1P001')==(kind=='dwf'),(path,kind)
    # The independent reader chooses its codec by suffix; use a same-byte copy
    # for the two explicit-format override cases.
    normalized=work/(backend+'-'+label+'-normalized.'+kind);normalized.write_bytes(path.read_bytes())
    assert stream(normalized)==reference,(model,backend,label,'complete ordered stream')
 report.update(status='PASS',negative_cases=len(negatives),real_parallel_partitions=2)
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS report-v3:',report['captures'],'captures,',report['rollbacks'],'rollbacks,',report['negative_cases'],'rejections')
