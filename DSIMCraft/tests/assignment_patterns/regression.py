"""Context-determined assignment patterns: types, timing, frames and replay."""
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
 source=fixtures/(name+'.sv')
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
  for port in ['one','two']:assert state[('top',port)][2][-1][1]==(0x7403,0)
 if name in ['timing','automatic','nested']:
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
 print('PASS assignment patterns',name,flush=True)

negative={
 'enum_bits':("typedef enum logic[1:0]{A=1,B=2} e;e q;initial q='{1,0};",'assignment pattern cannot construct an enum'),
 'too_many':("integer a[2];initial a='{1,2,3};",'too many assignment pattern entries'),
 'missing':("integer a[2];initial a='{1};",'leaves an element/member unassigned'),
 'out_of_range':("integer a[2];initial a='{3:1,default:0};",'index is out of range'),
 'duplicate_index':("integer a[2];initial a='{0:1,0:2,default:0};",'duplicate assignment pattern'),
 'duplicate_default':("integer a[2];initial a='{default:1,default:2};",'duplicate default'),
 'mixed':("integer a[2];initial a='{1,default:2};",'cannot mix positional and keyed'),
 'unknown_member':("typedef struct packed{logic a,b;} t;t q;initial q='{c:1,default:0};",'unknown assignment pattern member'),
 'duplicate_member':("typedef struct packed{logic a,b;} t;t q;initial q='{a:1,a:0,default:0};",'duplicate assignment pattern'),
 'struct_index':("typedef struct packed{logic a,b;} t;t q;initial q='{0:1,default:0};",'requires member names'),
 'enum_value':("typedef enum logic[1:0]{A=1,B=2} e;typedef struct packed{e mode;} t;t q;initial q='{mode:1};",'enum assignment requires'),
 'union':("typedef union packed{logic[3:0] a,b;} t;t q;initial q='{a:1};",'packed union assignment patterns'),
 'repeat_zero':("integer a[2];initial a='{0{1}};",'repetition count must be positive'),
 'repeat_large':("integer a[2];initial a='{1048577{1}};",'repetition count must be positive'),
 'repeat_runtime':("integer n,a[2];initial a='{n{1}};",'key/count must be a known integral constant'),
 'key_unknown':("integer a[2];initial a='{1'bx:1,default:0};",'known 32-bit integral constant'),
 'nested_missing':("integer a[2][2];initial a='{default:7};",'requires a pattern at each dimension'),
 'side_effect':("integer n=0,a[2];initial a='{n++,1};",'must have no persistent side effects'),
 'automatic_nba':("task automatic t();integer a[2];a<='{1,2};endtask initial t();",'nonblocking assignment to an automatic variable'),
 'unsupported_context':("initial $display(\"%b\",'{1,2});",'requires a supported assignment context'),
}

for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module top;'+source+' endmodule\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
 run([compiler,path,'--emit-only','--emit-cpp',dest],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text())
 assert not dest.exists(),name
path=out/'verilog-mode.v';path.write_text("module top;integer a[2];initial a='{1,2};endmodule\n")
run([compiler,path,'--language','verilog','--emit-only','--emit-cpp',out/'verilog-mode.cpp'],out,'verilog-mode',False)
assert 'assignment patterns require SystemVerilog mode' in (out/'verilog-mode.stderr').read_text()
# Check the parallel backend really scheduled independent worker partitions.
parallel_ir=json.loads((out/'parallel/parallel.json').read_text())
assert parallel_ir['parallel']['partitions']==2
report.update(status='PASS',negative_cases=len(negative)+1,real_parallel_partitions=2)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS assignment patterns compatibility',report['captures'],'captures and',report['rollbacks'],'rollbacks')
