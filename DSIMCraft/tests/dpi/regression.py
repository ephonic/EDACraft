"""Actual C ABI calls, callbacks, waves, input protection and prediction barriers."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]) if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={s.split('=',1)[0].split(':',1)[0]:s.split('=',1)[1] for s in cache.read_text().splitlines() if '=' in s and not s.startswith('//')}
fixtures=ROOT/'tests/dpi';expected=json.loads((fixtures/'expected.json').read_text())
report=dict(status='RUNNING',models={},captures=0,rollbacks=0,commits=0,negative_cases=0,runtime_rejections=0)
def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
def run(args,work,label,ok=True):
 p=subprocess.run(list(map(str,args)),cwd=work,text=True,capture_output=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode>=0 and (p.returncode==0)==ok,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout
def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,kind,value in events:
  if kind=='value':values[value[0]].append((t,value[1]))
 return {key:(width,ranges,values[i]) for key,(i,width,ranges) in declarations(meta).items()}
def native(source,exe,work,label):
 strict=['-fp-model=strict'] if Path(config['DSIM_MODEL_CXX']).name in ('icpx','icpc') else []
 export=['-Wl,-export_dynamic'] if sys.platform=='darwin' else ['-Wl,--export-dynamic','-ldl']
 return run([config['DSIM_MODEL_CXX'],'-std=c++17','-O2','-pthread',*strict,'-I'+config['DSIM_ZSTD_INCLUDE'],source,config['DSIM_ZSTD_LIBRARY'],*export,'-o',exe],work,label)
cc=os.environ.get('CC','cc')
feature_flags=[] if sys.platform=='darwin' else ['-D_GNU_SOURCE']
shared_flags=['-shared','-fPIC',*feature_flags,*(['-Wl,-undefined,dynamic_lookup'] if sys.platform=='darwin' else [])]
library=out/('api.dylib' if sys.platform=='darwin' else 'api.so')
run([cc,*shared_flags,'-I'+str(ROOT/'include/dsim'),fixtures/'api.c','-o',library],out,'c-library')
save()
for name,wanted in expected.items():
 work=out/name;work.mkdir(exist_ok=True);reference={}
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,fixtures/(name+'.sv'),'--wave-support','--dpi-lib',library,'--dpi-header',work/(backend+'.h'),*flags,'--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
  run([cc,*feature_flags,'-fsyntax-only','-I'+str(ROOT/'include/dsim'),'-include',work/(backend+'.h'),fixtures/'api.c'],work,backend+'-c-prototypes')
  stdout=run([work/backend],work,backend+'-run')
  assert stdout.splitlines()==wanted,(name,backend,stdout,wanted)
  for mode in ['ordered','settled']:
   for fmt,extra in [('vcd',[]),('dwf',[]),('async.dwf',['--wave-async','--wave-buffer-bytes','4096'])]:
    path=work/(backend+'-'+mode+'.'+fmt);path.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',path,'--wave-format','vcd' if fmt=='vcd' else 'dwf','--wave-mode',mode,*extra],work,backend+'-'+mode+'-'+fmt)==stdout
    state=streams(path);report['captures']+=1
    if backend=='serial' and fmt=='vcd':reference[mode]=state
    assert state==reference[mode],(name,backend,mode,fmt)
    if fmt=='async.dwf':assert path.read_bytes()==(work/(backend+'-'+mode+'.dwf')).read_bytes()
 if name=='rollback':
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  replacement='''
s.run_until(0);
if(s.predict_until(3,[](Sim&){},[](const Sim&){return true;},[](Sim&){}))throw std::runtime_error("impure call was speculated");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing foreign-call rollback");
s.run_until(4);
if(s.predict_until(5,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("unexpected pure commit");
if(!s.predict_until(6,[](Sim&){},[](const Sim&){return true;},[](Sim&){}))throw std::runtime_error("missing pure commit");
s.run();
'''
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n',replacement));native(work/'replay.cpp',work/'replay',work,'replay-compile')
  path=work/'replay.dwf';path.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',path,'--wave-mode','ordered','--wave-async'],work,'replay-run')==stdout
  assert streams(path)==reference['ordered'];report['captures']+=1;report['rollbacks']+=2;report['commits']+=1
  path=work/'selected.dwf';path.unlink(missing_ok=True)
  run([work/'serial','--waveform',path,'--wave-async','--wave-scope','top','--wave-include','*observed','--wave-start','3','--wave-end','4'],work,'selected-run')
  lanes=timeline(*read(path));assert set(lanes)=={('top','observed')} and lanes[('top','observed')][2]==[(3,(1,0)),(4,(2,0))],lanes;report['captures']+=1
  run([work/'parallel','--parallel-stats'],work,'parallel-stats')
  assert '"partitions":1' in (work/'parallel-stats.stderr').read_text()
 report['models'][name]=dict(status='PASS',source_sha256=hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest());save()
# Reject unsupported signatures even when there is no SV call site.
for name,(body,diagnostic) in json.loads((fixtures/'negative.json').read_text()).items():
 source=out/(name+'.sv');source.write_text('module top;'+body+'\nendmodule\n');target=out/(name+'.cpp');target.unlink(missing_ok=True)
 run([compiler,source,'--emit-only','--emit-cpp',target],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),name
 assert not target.exists(),(name,'partial generated output');report['negative_cases']+=1;save()
# Output protections include binary libraries, generated headers and symlink aliases.
for label,flags in [('cpp-library',['--emit-cpp',library]),('header-library',['--dpi-header',library]),('header-source',['--dpi-header',fixtures/'atoms.sv']),('header-cpp',['--dpi-header',out/'same.cpp','--emit-cpp',out/'same.cpp'])]:
 before=hashlib.sha256(library.read_bytes()).hexdigest()
 run([compiler,fixtures/'atoms.sv','--dpi-lib',library,'--emit-only',*flags],out,label,False)
 assert hashlib.sha256(library.read_bytes()).hexdigest()==before
 report['negative_cases']+=1
# Runtime library override, missing paths/symbols and invalid callback context.
assert run([out/'atoms/serial','--dpi-lib',library],out,'override')=='\n'.join(expected['atoms'])+'\n'
for label,args,diagnostic in [('missing-library',[out/'atoms/serial','--dpi-lib',out/'absent.so'],'DPI library'),('missing-runtime-path',[out/'atoms/serial','--dpi-lib'],'requires a path')]:
 run(args,out,label,False);assert diagnostic in (out/(label+'.stderr')).read_text();report['runtime_rejections']+=1
source=out/'missing.sv';source.write_text('module top;import "DPI-C" function int missing_symbol(); initial $display("%0d",missing_symbol());endmodule\n')
run([compiler,source,'--emit-cpp',out/'missing.cpp','-o',out/'missing'],out,'missing-compile')
run([out/'missing'],out,'missing-run',False);assert 'DPI symbol not found: missing_symbol' in (out/'missing-run.stderr').read_text();report['runtime_rejections']+=1
source=out/'ordinary-callback.sv';source.write_text('module top;import "DPI-C" function int bad_callback(int x);export "DPI-C" function hook;function int hook(int x);return x;endfunction initial $display("%0d",bad_callback(1));endmodule\n')
run([compiler,source,'--dpi-lib',library,'--emit-cpp',out/'ordinary-callback.cpp','-o',out/'ordinary-callback'],out,'ordinary-callback-compile')
run([out/'ordinary-callback'],out,'ordinary-callback-run',False);assert 'requires a context import' in (out/'ordinary-callback-run.stderr').read_text();report['runtime_rejections']+=1
source=out/'wrong-scope.sv';source.write_text('module child;export "DPI-C" function hook;function int hook(int x);return x;endfunction endmodule module top;child u();import "DPI-C" context function int wrong_scope(int x);initial $display("%0d",wrong_scope(1));endmodule\n')
run([compiler,source,'--dpi-lib',library,'--emit-cpp',out/'wrong-scope.cpp','-o',out/'wrong-scope'],out,'wrong-scope-compile')
run([out/'wrong-scope'],out,'wrong-scope-run',False);assert 'DPI export not found in scope: top.hook' in (out/'wrong-scope-run.stderr').read_text();report['runtime_rejections']+=1
report['status']='PASS';save();print('PASS DPI:',report['captures'],'captures,',report['rollbacks'],'rollbacks,',report['commits'],'commit,',report['negative_cases'],'compile rejections,',report['runtime_rejections'],'runtime rejections')
