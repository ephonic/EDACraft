"""Packed variable selects: four states, clipping, sampled targets and rollback."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
def run(cmd,work,label,ok=True):
 p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert (p.returncode==0)==ok,(label,p.stdout,p.stderr)
 return p.stdout
def streams(stream):
 meta,events=stream;values=[[] for _ in meta['signals']]
 for time,kind,payload in events:
  if kind=='value':values[payload[0]].append((time,payload[1]))
 return {name:(width,ranges,values[ident]) for name,(ident,width,ranges) in declarations(meta).items()}
expected={
 'design':['TRACE reads=1 5 d 5a bcdeffedcba987654321','TRACE folded=5 5 a','TRACE partial=xx11 011010xx 010x','TRACE clipped=X35d c37c',
 'TRACE unknown=x '+'x'*80,'TRACE large=x '+'x'*16,'TRACE unchanged=X35d c37c 0123456789abcdeffedcba9876543210',
 'TRACE widewrite=0123456789axz0123456789abcdef010 xxxxzzzz000000010010001101000101011001111000100110101011110011011110111100000001',
 'TRACE overlap=0d50','TRACE nba=0008','TRACE delayed=0508','TRACE blocking=2948 index=  6','TRACE final=2948'],
 'narrow':['TRACE first=5 port=5','TRACE index=3','TRACE changed=9 q=c95a','TRACE upper=xxx1','TRACE x=xxxx','TRACE ignored=c95a'],
 'large_index':['TRACE large=x xxxxxxxx','TRACE unchanged=123456789abcdef0123456789abcdef0','TRACE unknown-high=xxxxxxxx'],
 'parallel':[]}
captures=0
for name in expected:
 work=out/name;work.mkdir(exist_ok=True);reference={}
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,ROOT/'tests/indexed_selects'/(name+'.sv'),'--wave-support',*flags,'--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
  trace=run([work/backend],work,backend+'-none')
  assert trace.splitlines()==expected[name],(name,backend,trace)
  for mode in ['ordered','settled']:
   for fmt in ['vcd','dwf']:
    dest=work/(backend+'-'+mode+'.'+fmt);dest.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',dest,'--wave-format',fmt,'--wave-mode',mode],work,backend+'-'+mode+'-'+fmt)==trace
    stream=read(dest);captures+=1
    if backend=='serial' and fmt=='vcd':reference[mode]=stream
    assert streams(stream)==streams(reference[mode]),(name,backend,mode,fmt)
  if name=='parallel' and backend=='parallel':
   run([work/backend,'--parallel-stats'],work,'stats')
   assert '"partitions":2' in (work/'stats.stderr').read_text()
 if name in ['design','narrow']:
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
s.run_until(1);
if(s.predict_until(20,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("unexpected prediction commit");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing rollback");
s.run();
'''))
  cache=(compiler.parent/'CMakeCache.txt').read_text().splitlines()
  config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache if '=' in x and not x.startswith('//')}
  run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  dest=work/'replay.dwf';dest.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',dest,'--wave-mode','ordered'],work,'replay-run').splitlines()==expected[name]
  assert streams(read(dest))==streams(reference['ordered']);captures+=1
negative={
 'dynamic-width':'reg[7:0] q;reg[2:0] i;initial q[i+:i]=0;',
 'dynamic-range':'reg[7:0] q;reg[2:0] i;initial q[i:0]=0;',
 'zero-width':'reg[7:0] q;reg[2:0] i;initial q[i+:0]=0;',
 'continuous-target':'wire[7:0] q;reg[2:0] i;assign q[i]=1;',
 'port-target':'wire[7:0] q;reg[2:0] i;child u(q[i]);',
 'comb-feedback':'logic[7:0] q;logic[2:0] i;always_comb q[i]=q[0];',
 'ff-overlap':'logic[7:0] q;logic[2:0] i;logic c;always_ff @(posedge c)q[i]<=0;always_ff @(posedge c)q[7]<=1;',
}
for name,body in negative.items():
 work=out/name;work.mkdir(exist_ok=True)
 (work/'bad.sv').write_text('module child(output a);assign a=0;endmodule\nmodule top;'+body+'endmodule\n')
 run([compiler,work/'bad.sv','--emit-only','--emit-cpp',work/'bad.cpp'],work,'reject',False)
(out/'results.json').write_text(json.dumps(dict(status='PASS',captures=captures,negative_cases=len(negative),rollback_models=2),indent=2)+'\n')
print('PASS indexed selects:',captures,'captures,',len(negative),'rejections, 2 rollback models')
