"""Compiled memories: addressing, delays, file input, waveforms and rollback."""
from pathlib import Path
import json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/memory'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in (compiler.parent/'CMakeCache.txt').read_text().splitlines() if '=' in x and not x.startswith('//')}
def run(cmd,work,label,ok=True):
 p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert (p.returncode==0)==ok,(label,p.stdout,p.stderr)
 return p.stdout

def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
expected={
 'design':['TRACE init 12 2 90 0123456789abcdef0123 xx','TRACE part f4 f ab','TRACE nba a5 ac de 72 zzzzzzzzzzzzzzzzZbZz','TRACE ram c7','TRACE block 12 81','TRACE outside xx x','TRACE unknown xx xx xxxxxxxxxxxxxxxxxxxx','TRACE huge xx 12 72'],
 'parallel':[],
 'file_io':['TRACE hex 12 cd xx xx zz 1x 99','TRACE bin 000010xz 10100101 xxxxxxxx zzzzzzzz','TRACE wide 0123456789abcdef0123 xxxxxxxxxxxxxxxxxxxx zzzzzzzzzzzzzzzzzzzz','TRACE reverse 11 22 33','TRACE q 22'],
 'narrow':['TRACE scalar 1 seen=1','TRACE outside x']}
captures=0
for name,wanted in expected.items():
 work=out/name;work.mkdir(exist_ok=True);references={}
 for source in fixtures.iterdir():
  if source.suffix in ['.hex','.bin']:shutil.copyfile(source,work/source.name)
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,fixtures/(name+'.sv'),'--wave-support',*flags,'--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
  trace=run([work/backend],work,backend+'-run');assert trace.splitlines()==wanted,(name,backend,trace)
  for mode in ['ordered','settled']:
   for fmt in ['vcd','dwf']:
    dest=work/(backend+'-'+mode+'.'+fmt);dest.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',dest,'--wave-mode',mode,'--wave-format',fmt],work,backend+'-'+mode+'-'+fmt)==trace
    state=streams(dest);captures+=1
    if backend=='serial' and fmt=='vcd':references[mode]=state
    assert state==references[mode],(name,backend,mode,fmt)
  if backend=='parallel' and name in ['parallel','narrow']:
   run([work/backend,'--parallel-stats'],work,'stats')
   assert '"partitions":2' in (work/'stats.stderr').read_text()
 if name=='parallel':
  state=timeline(*read(work/'serial-settled.vcd'))
  for unit,seed in [('u',3),('v',17)]:
   for i in range(16):
    key=('top',unit,f'mem[{i}]');assert state[key][2]==[(0,(seed+i,0)),((i+2)*1000,(seed+i+1,0))],(key,state[key])
 if name in ['design','file_io']:
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
if(s.predict_until(20000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
  run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  dest=work/'replay.dwf';dest.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',dest,'--wave-mode','ordered'],work,'replay-run').splitlines()==wanted
  assert streams(dest)==references['ordered'];captures+=1
negative={
 'subarray_value':'reg[7:0] a[0:2][0:2];reg[7:0] q;initial q=a[0];',
 'negative-bounds':'reg[7:0] a[-1:2];',
 'whole-array':'reg[7:0] a[0:2];reg[7:0] q;initial q=a;',
 'runtime-filename':'reg[7:0] a[0:2];reg[7:0] f;initial $readmemh(f,a);',
 'ff-conflict':'reg c;logic[7:0] a[0:3];reg[1:0] i;always_ff @(posedge c)a[i]<=0;always_ff @(posedge c)a[2]<=1;',
}
for name,body in negative.items():
 work=out/name;work.mkdir(exist_ok=True)
 text='module top;\n'+body+'\nendmodule\n'
 (work/'bad.sv').write_text(text)
 run([compiler,work/'bad.sv','--emit-only','--emit-cpp',work/'bad.cpp'],work,'reject',False)
 assert 'dsim:' in (work/'reject.stderr').read_text()
# These declarations became supported before M103. Both the M102 stable
# entry and the current compiler accept them; they are no longer negatives.
for label,text in [('array-port','module top(input [7:0] a[0:2]);endmodule\n'),
                   ('net-array','module top;wire[7:0] a[0:2];endmodule\n')]:
 source=out/(label+'-supported.sv');source.write_text(text)
 run([compiler,source,'--emit-only','--emit-cpp',out/(label+'-supported.cpp')],out,label+'-supported')
# Runtime diagnostics use a narrow model to exercise the non-wide reader too.
work=out/'invalid-file';work.mkdir(exist_ok=True)
(work/'top.sv').write_text('module top;reg[7:0] a[0:2];initial $readmemh("bad.hex",a);endmodule\n')
run([compiler,work/'top.sv','-o',work/'simv'],work,'compile')
for label,data in [('digit','gg'),('comment','/*oops'),('address','@10000000000000000000000 12'),('excess','01 02 03 04')]:
 (work/'bad.hex').write_text(data)
 run([work/'simv'],work,label,False)
 assert 'bad.hex:' in (work/(label+'.stderr')).read_text()
(work/'bad.hex').unlink();run([work/'simv'],work,'missing',False)
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=4,captures=captures,negative_cases=len(negative),runtime_rejections=5,rollback_models=2,supported_compile_probes=2),indent=2)+'\n')
print('PASS memory:',captures,'captures,',len(negative),'compile rejections, 5 file diagnostics, 2 rollback models')
