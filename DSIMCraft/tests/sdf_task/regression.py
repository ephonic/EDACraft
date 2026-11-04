"""Static annotation must execute the same paths as explicit CLI annotation."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
from cases import make
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,bit_timeline
p=argparse.ArgumentParser();p.add_argument('compiler',type=Path);p.add_argument('out',type=Path);p.add_argument('--vcs',type=Path);p.add_argument('--negative-only',action='store_true');a=p.parse_args()
out=a.out.resolve();compiler=a.compiler.resolve();cases=make(out)
def run(command,w,label,ok=True):
 command=list(map(str,command));r=subprocess.run(command,cwd=w,capture_output=True,text=True,timeout=300)
 (w/(label+'.command.json')).write_text(json.dumps(command)+'\n')
 (w/(label+'.stdout')).write_text(r.stdout);(w/(label+'.stderr')).write_text(r.stderr)
 assert (r.returncode==0)==ok,(label,r.returncode,r.stdout,r.stderr)
 assert not any(s in r.stderr for s in ('AddressSanitizer','runtime error:','DEADLYSIGNAL'))
 return r
results={}
for name,case in ([] if a.negative_only else cases.items()):
 w=out/name
 common=[compiler,'--gate-netlist',w/'net.v','--gate-top','dut','--gate-models',w/'cells.v','--liberty',w/'cells.lib','--wave-support',*case['flags']]
 log=w/'annotation.log';log.unlink(missing_ok=True)
 run([*common,w/'tb.v','--emit-ir',w/'ir.json','--emit-preprocessed',w/'expanded.v','--emit-deps',w/'deps.json','-o',w/'native'],w,'compile')
 expanded=run([compiler,'-E',w/'tb.v'],w,'preprocess')
 assert (w/'expanded.v').read_text()==expanded.stdout,'deferred output must preserve compiler directives'
 assert not log.exists(),'log must be written by simulation, not code generation'
 ir=json.loads((w/'ir.json').read_text());assert ir['sdf_static_tasks']==1 and ir['global_precision_fs']==1000 and ir['gate_design']['sdf_runtime']
 assert str(w/'delay.sdf') in (w/'deps.json').read_text()
 native=run([w/'native','--waveform',w/'native.vcd','--wave-format','vcd'],w,'run')
 trace=[l for l in native.stdout.splitlines() if l.startswith('TRACE ')]
 pins=bit_timeline(*read(w/'native.vcd'))
 if case['log']:
  report=json.loads(log.read_text());assert report['binding']['corner']==['min','typ','max'][case['corner']]
 else:assert not log.exists()
 run([*common,'--sdf-annotate',w/'delay.sdf','--sdf-corner',['min','typ','max'][case['corner']],w/'baseline.v','-o',w/'baseline'],w,'baseline-compile')
 baseline=run([w/'baseline','--waveform',w/'baseline.vcd','--wave-format','vcd'],w,'baseline-run')
 assert trace==[l for l in baseline.stdout.splitlines() if l.startswith('TRACE ')],name
 assert pins==bit_timeline(*read(w/'baseline.vcd')),name
 if a.vcs:
  ref=a.vcs/name
  for f in ['tb.v','cells.v','net.v','delay.sdf']:assert (w/f).read_bytes()==(ref/f).read_bytes(),(name,f)
  assert trace==[l for l in (ref/'run.stdout').read_text().splitlines() if l.startswith('TRACE ')],name
  reference=bit_timeline(*read(ref/'vcs.vcd'))
  for signal in ('A','Z'):assert pins[('top',signal,None)]==reference[('top',signal,None)],(name,signal)
 results[name]=dict(status='PASS',trace=trace,log_at_runtime=case['log'],vcs_compared=bool(a.vcs),cpp_sha256=hashlib.sha256((w/'native.dsim.cpp').read_bytes()).hexdigest())
 print('PASS static SDF task',name,flush=True)
# Rejections preserve every output and the actual SDF input, including aliases.
w=out/'direct';tb=w/'tb.v';original=tb.read_text();sdf=w/'delay.sdf';raw=sdf.read_bytes()
protected=w/'protected.cpp';ir=w/'protected.json';aux=w/'protected.v';deps=w/'protected-deps.json'
for file in (protected,ir,aux,deps):file.write_text('keep')
args=[compiler,'--gate-netlist',w/'net.v','--gate-top','dut','--gate-models',w/'cells.v','--liberty',w/'cells.lib',tb,'--emit-only','--emit-cpp',protected,'--emit-ir',ir,'--emit-preprocessed',aux,'--emit-deps',deps]
call=cases['direct']['task'];rejects=0
def reject(label,replacement,message,extra=()):
 global rejects
 tb.write_text(original.replace(call,replacement))
 r=run([*args,*extra],w,label,False);assert message in r.stderr,(label,r.stderr)
 assert sdf.read_bytes()==raw
 for file in (protected,ir,aux,deps):assert file.read_text()=='keep',file
 rejects+=1
reject('delayed','initial begin #1;$sdf_annotate("delay.sdf",d);end','unconditional time-zero')
reject('delta','initial begin #0;$sdf_annotate("delay.sdf",d);end','unconditional time-zero')
reject('conditional','initial if(A)$sdf_annotate("delay.sdf",d);','unconditional time-zero')
reject('always','always @(A)$sdf_annotate("delay.sdf",d);','unconditional time-zero')
reject('final','final $sdf_annotate("delay.sdf",d);','unconditional time-zero')
reject('after-finish','initial begin $finish;$sdf_annotate("delay.sdf",d);end','unconditional time-zero')
reject('multiple',call+call,'multiple $sdf_annotate')
reject('default-target','initial $sdf_annotate("delay.sdf");','explicit structural gate root')
reject('bad-target','initial $sdf_annotate("delay.sdf",A);','target must be a module instance')
reject('dynamic-file','string file="delay.sdf";initial $sdf_annotate(file,d);','elaboration-constant string')
reject('nul-filename',r'initial $sdf_annotate("delay.sdf\000suffix",d);','embedded NUL')
reject('bad-corner','initial $sdf_annotate("delay.sdf",d,,,"FAST");','unsupported $sdf_annotate mtm_spec')
reject('scale','initial $sdf_annotate("delay.sdf",d,,,,"2:2:2");','scale_factors/scale_type')
(w/'config.txt').write_text('existing configuration')
reject('existing-config','initial $sdf_annotate("delay.sdf",d,"config.txt");','configuration files are not implemented')
reject('conflicting-cli',call,'do not combine',['--sdf-annotate',sdf])
reject('tick',call,'omit --sdf-tick',['--sdf-tick','1ps'])
reject('log-input','initial $sdf_annotate("delay.sdf",d,,"delay.sdf");','log would overwrite an input')
for label,alias in [('symlink',w/'sym.sdf'),('hardlink',w/'hard.sdf')]:
 alias.unlink(missing_ok=True)
 if label=='symlink':alias.symlink_to(sdf)
 else:os.link(sdf,alias)
 reject('log-'+label,'initial $sdf_annotate("delay.sdf",d,,"'+alias.name+'");','log would overwrite an input')
reject('namespace-value','initial $display("%d",d);','module instance is a namespace')
reject('namespace-filename','initial $sdf_annotate(d,d);','module instance is a namespace')
for option in ('--emit-preprocessed','--emit-deps','--emit-cpp','-o'):
 reject('source'+option.replace('-',''),call,'output would overwrite SDF task input',[option,sdf])
reject('log-output','initial $sdf_annotate("delay.sdf",d,,"protected.cpp");','log conflicts with a compiler output')
reject('sdf-output','initial $sdf_annotate("protected.cpp",d);','output would overwrite SDF task input')
tb.write_text(original.replace('dut d(A,Z);','dut d(A,Z);wire W;dut e(A,W);'))
r=run(args,w,'two-instances',False);assert 'exactly one structural gate instance' in r.stderr;rejects+=1
tb.write_text(original)
(out/'results.json').write_text(json.dumps(dict(status='PASS',cases=results,rejections=rejects),indent=2)+'\n')
print('PASS SDF task strict rejections',rejects,flush=True)
