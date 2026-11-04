"""Integer and static lexical variables through the actual compiled flow."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/integer'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in (compiler.parent/'CMakeCache.txt').read_text().splitlines() if '=' in x and not x.startswith('//')}
def run(cmd,work,label,ok=True):
 p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode>=0,(label,"process crashed",p.returncode,p.stderr)
 assert (p.returncode==0)==ok,(label,p.stdout,p.stderr)
 return p.stdout

def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}

expected=json.loads((fixtures/'expected.json').read_text())
captures=0
for name,wanted in expected.items():
 work=out/name;work.mkdir(exist_ok=True);references={}
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,fixtures/(name+'.sv'),'--wave-support',*flags,'--emit-ir',work/(backend+'.json'),'--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
  trace=run([work/backend],work,backend+'-run');assert trace.splitlines()==wanted,(name,backend,trace)
  if name=='scopes':
   report=json.loads((work/(backend+'.json')).read_text());top=next(s for s in report['scopes'] if s['path']=='top')
   assert top['signals']['value']['signed'] and top['signals']['value']['width']==32
   paths={s['path']:s for s in report['scopes']}
   assert paths['top.outer']['signals']['value']['signed']
   assert paths['top.outer.tick']['signals']['visits']['signed']
  for mode in ['ordered','settled']:
   for fmt in ['vcd','dwf']:
    dest=work/(backend+'-'+mode+'.'+fmt);dest.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',dest,'--wave-mode',mode,'--wave-format',fmt],work,backend+'-'+mode+'-'+fmt)==trace
    state=streams(dest);captures+=1
    if backend=='serial' and fmt=='vcd':references[mode]=state
    assert state==references[mode],(name,backend,mode,fmt)
  if backend=='parallel' and name=='parallel':
   run([work/backend,'--parallel-stats'],work,'stats')
   assert '"partitions":2' in (work/'stats.stderr').read_text()
 if name=='parallel':
  values=timeline(*read(work/'serial-settled.vcd'))
  for signal,base in [('a',7),('b',31)]:
   expected_values=[]
   for i in range(6):
    stimulus=0 if i==0 else base-(i-1)*7
    quotient=abs(stimulus)//3*(-1 if stimulus<0 else 1)
    value=(quotient-base)&0xffffffff
    item=(i*1000,(value,0))
    if not expected_values or expected_values[-1][1]!=item[1]:expected_values.append(item)
   assert values[('top',signal)][2]==expected_values,(signal,values[('top',signal)],expected_values)
 if name=='memory':
  values=timeline(*read(work/'serial-settled.vcd'))
  expected_words={2:[(0,(0xfffffffe,0)),(3000,(0xffffff80,0))],3:[(0,(0xfffffffd,0)),(2000,(0xfffffff6,0))],4:[(0,(0xfffffffc,0)),(1000,(0xffffff9d,0))],5:[(0,(0xfffffffb,0))]}
  for word,wanted_word in expected_words.items():assert values[('top',f'mem[{word}]')][2]==wanted_word,(word,values)
 if name in ['scopes','memory']:
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
if(s.predict_until(300000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
  run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  dest=work/'replay.dwf';dest.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',dest,'--wave-mode','ordered'],work,'replay-run').splitlines()==wanted
  assert streams(dest)==references['ordered'];captures+=1
# Compile-time boundaries and lexical visibility must fail explicitly.
negative={
 'scope_escape':('module top; initial begin integer private_value; end initial private_value=1; endmodule',''),
 'subarray_value':('module top; integer mem[0:2][0:3],q; initial q=mem[0]; endmodule',''),
 'negative_bounds':('module top; integer mem[-2:2]; endmodule','nonnegative'),
 'packed_integral':('module top; output integer [7:0] a; endmodule',''),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text(source+'\n')
 run([compiler,path,'--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert 'dsim:' in (out/(name+'.stderr')).read_text(),name
 assert diagnostic in (out/(name+'.stderr')).read_text(),name
print('PASS',len(negative),'unsupported or invalid declaration diagnostics')

# Explicit automatic locals reset on each entry into a default-static block.
path=out/'automatic_local.sv'
path.write_text('module top;integer q=0;initial begin repeat(3)begin automatic integer i=0;i++;q+=i;end if(q!=3)$fatal(1,"automatic local reset");end endmodule\n')
run([compiler,path,'-o',out/'automatic_local'],out,'automatic_local-compile')
assert run([out/'automatic_local'],out,'automatic_local-run')==''

(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=2,negative_cases=len(negative),independent_integer_words=4,independent_parallel_lanes=2),indent=2)+'\n')
print('PASS integer:',captures,'captures, 2 rollback models,',len(negative),'diagnostics')
