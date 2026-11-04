"""Package defaults, explicit subroutine lifetime, replay and keyword modes."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache_path=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
cache={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache_path.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations,timeline

def run(command,work,label,ok=True):
 p=subprocess.run(list(map(str,command)),cwd=work,text=True,capture_output=True,timeout=300)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==(0 if ok else 1),(label,p.returncode,p.stdout[-2000:],p.stderr[-2000:])
 return p.stdout

def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}

expected=json.loads((fixtures/'expected.json').read_text())
report=dict(status='RUNNING',models={},captures=0,commits=0,rollbacks=0,negative_cases=0)
try:
 for name,wanted in expected.items():
  work=out/name;work.mkdir(exist_ok=True);reference=None
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,fixtures/(name+'.sv'),*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-compile')
   wave=work/(backend+'.vcd');wave.unlink(missing_ok=True)
   text=run([work/backend,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,backend+'-run')
   assert [x for x in text.splitlines() if x.startswith('TRACE')]==wanted,(name,backend,text,wanted)
   current=(text,stream(wave))
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete per-signal ordered streams')
   report['captures']+=1
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  cxx=cache.get('DSIM_MODEL_CXX',cache['CMAKE_CXX_COMPILER'])
  if Path(cxx).name=='clang++' and sys.platform=='darwin':cxx='c++'
  cflags=['-fp-model=strict'] if Path(cxx).name in ['icpx','icpc'] else []
  def native(cpp,label):
   run([cxx,'-std=c++17','-O2','-pthread',*cflags,'-I'+cache['DSIM_ZSTD_INCLUDE'],cpp,cache['DSIM_ZSTD_LIBRARY'],'-o',work/label],work,label+'-compile')
  for accept in [False,True]:
   label='commit' if accept else 'rollback';cpp=work/(label+'.cpp')
   patch='''
s.run_until(500);
bool accepted=s.predict_until(95000,[](Sim&){},[](const Sim&){return ACCEPT;},[](Sim&){});
if(accepted!=ACCEPT||s.prediction_stats.COUNTER!=1)throw std::runtime_error("package transaction mismatch");
s.run();
'''.replace('ACCEPT',str(accept).lower()).replace('COUNTER','commits' if accept else 'rollbacks')
   cpp.write_text(code.replace('\ns.run();\n',patch));native(cpp,label)
   wave=work/(label+'.vcd');wave.unlink(missing_ok=True)
   text=run([work/label,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,label+'-run')
   assert (text,stream(wave))==reference,(name,label,'transaction state or wave')
   report['captures']+=1;report['commits' if accept else 'rollbacks']+=1
  ir=json.loads((work/'parallel.json').read_text())
  if name=='parallel':
   assert ir['parallel']['partitions']==2,ir['parallel']
   values=timeline(*read(work/'parallel.vcd'))
   for port,wanted_value in [('one',9),('two',18)]:assert values[('top',port)][2][-1][1]==(wanted_value,0),port
   run([work/'parallel','--parallel-stats'],work,'parallel-stats');assert '"partitions":2' in (work/'parallel-stats.stderr').read_text()
  if name=='overlap':
   assert ir['parallel']['partitions']==1,'shared package state must remain in one partition'
   ids=sorted({row['id'] for scope in ir['scopes'] for row in scope['signals'].values()})
   values='std::vector<V>{'+','.join('s.get('+str(i)+')' for i in ids)+'}'
   probe='s.run_until(1500);auto cp=s.checkpoint();s.run();auto final='+values+';auto steps=s.executed_steps();s.restore(cp);s.restore(cp);s.run();auto again='+values+';if(s.executed_steps()!=steps)throw std::runtime_error("checkpoint steps");for(size_t i=0;i<final.size();++i)if(!final[i].same(again[i]))throw std::runtime_error("checkpoint package state");'
   cpp=work/'checkpoint.cpp';cpp.write_text(code.replace('\ns.run();\n',probe));native(cpp,'checkpoint')
   assert run([work/'checkpoint'],work,'checkpoint-run').splitlines()==wanted+wanted
   report['checkpoint_restores']=2
  report['models'][name]=dict(status='PASS',source_sha256=hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),trace=wanted,parallel_partitions=ir['parallel']['partitions'])
  print('PASS package lifetimes',name,flush=True)
 # A package's default automatic lifetime must activate existing restrictions.
 negatives={
  'function_nba': 'package automatic p;function integer f();integer n;n<=1;return n;endfunction endpackage module top;integer x;initial x=p::f();endmodule',
  'task_nba': 'package automatic p;task t();integer n;begin n<=1;end endtask endpackage module top;initial p::t();endmodule',
  'static_ref': 'package automatic p;task static t(ref integer n);begin n++;end endtask endpackage module top;integer x=1;initial p::t(x);endmodule',
  'duplicate_function': 'module top;function automatic automatic integer f();return 1;endfunction endmodule',
  'conflicting_function': 'module top;function automatic static integer f();return 1;endfunction endmodule',
  'conflicting_task': 'module top;task static automatic t();begin end endtask endmodule',
  'duplicate_package': 'package static static p;endpackage module top;endmodule',
  'conflicting_package': 'package static automatic p;endpackage module top;endmodule',
 }
 # Exercise unqualified and qualified identifier paths for each newly reserved word.
 # Keep this list independent of the scanner implementation.
 words='accept_on alias before bins binsof checker class clocking constraint context covergroup coverpoint cross dist endchecker endclass endclocking endgroup endprogram eventually expect extends extern first_match global ignore_bins illegal_bins implements implies interconnect intersect let local matches nettype nexttime null program protected pure rand randc randcase randsequence reject_on restrict s_always s_eventually s_nexttime s_until s_until_with shortreal soft solve strong super sync_accept_on sync_reject_on tagged this throughout timeprecision timeunit type until until_with untyped virtual weak wildcard within'.split()
 for word in words:
  negatives['keyword-'+word]='module top;integer '+word+';endmodule'
  negatives['qualified-'+word]='package p;integer good;endpackage module top;integer x;initial x=p::'+word+';endmodule'
 for name,body in negatives.items():
  path=out/(name+'.sv');path.write_text(body+'\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  run([compiler,path,'--emit-only','--emit-cpp',dest],out,name,False)
  assert not dest.exists(),name
  report['negative_cases']+=1
 # In Verilog mode the same SV keywords are ordinary names, including p::-free use.
 legacy=out/'legacy.v';legacy.write_text('module top;integer '+','.join(word+'=1' for word in words)+';initial $display("TRACE legacy %0d",'+ '+'.join(words)+');endmodule\n')
 run([compiler,legacy,'--language','verilog','-o',out/'legacy'],out,'legacy-compile')
 assert run([out/'legacy'],out,'legacy-run')=='TRACE legacy '+str(len(words))+'\n'
 escaped=out/'escaped.sv';escaped.write_text('module top;integer \\before =3, before_value=4;initial begin /* before */ $display("TRACE escaped before %0d",\\before +before_value);end endmodule\n')
 run([compiler,escaped,'-o',out/'escaped'],out,'escaped-compile')
 assert run([out/'escaped'],out,'escaped-run')=='TRACE escaped before 7\n'
 report.update(status='PASS',real_parallel_partitions=2,keyword_count=len(words),keyword_positive_modes=2)
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS package lifetimes:',report['captures'],'captures,',report['negative_cases'],'rejections')
