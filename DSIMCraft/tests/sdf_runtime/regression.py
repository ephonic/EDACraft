"""Run actual compiler-generated SDF paths. Optional fresh VCS evidence check."""
import argparse,json,subprocess,sys
from pathlib import Path
from cases import make
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,bit_timeline
expected_path=Path(__file__).with_name('expected.json')
expected=json.loads(expected_path.read_text())
p=argparse.ArgumentParser();p.add_argument('compiler',type=Path);p.add_argument('out',type=Path);p.add_argument('--vcs',type=Path);a=p.parse_args()
compiler=a.compiler.resolve();out=a.out.resolve();cases=make(out)
def run(cmd,w,name,ok=True):
 r=subprocess.run(list(map(str,cmd)),cwd=w,text=True,capture_output=True,timeout=180)
 (w/name).write_text(r.stdout+r.stderr);assert (r.returncode==0)==ok,(cmd,r.stdout,r.stderr)
 assert not any(x in r.stdout+r.stderr for x in ['AddressSanitizer','runtime error:','DEADLYSIGNAL'])
 return [x for x in r.stdout.splitlines() if x.startswith('TRACE ')]
def command(w):return [compiler,'--sdf-annotate',w/'delay.sdf','--gate-models',w/'cells.v','--gate-netlist',w/'net.v','--gate-top','dut','--liberty',w/'cells.lib',w/'tb.v']
results={}
for name,case in cases.items():
 w=out/name;run(command(w)+['--wave-support','--emit-ir',w/'ir.json','-o',w/'native'],w,'native-compile.log')
 ir=json.loads((w/'ir.json').read_text());assert ir['global_precision_fs']==1000 and ir['gate_design']['sdf_runtime']
 traces=[];waves=[]
 for i in range(3):
  dest=w/f'native-{i}.vcd';dest.unlink(missing_ok=True)
  traces.append(run([w/'native','--waveform',dest,'--wave-format','vcd'],w,f'native-{i}.log'))
  waves.append(bit_timeline(*read(dest)))
 assert all(t==traces[0] for t in traces) and all(w==waves[0] for w in waves)
 pins={pin:waves[0][('top',pin,None)] for pin in case['outputs']}
 if expected:
  assert traces[0]==expected[name]['trace'],(name,traces[0],expected[name]['trace'])
  assert json.loads(json.dumps(pins))==expected[name]['pins'],(name,pins,expected[name]['pins'])
 if a.vcs:
  ref=a.vcs.resolve()/name
  for f in ['cells.v','cells.lib','net.v','tb.v','delay.sdf']:assert (w/f).read_bytes()==(ref/f).read_bytes(),(name,f)
  for i in range(3):
   reference_trace=[x for x in (ref/f'run-{i}.log').read_text().splitlines() if x.startswith('TRACE ')]
   assert traces[0]==reference_trace,(name,traces[0],reference_trace)
   reference=bit_timeline(*read(ref/f'{i}-vcs.vcd'))
   for pin in case['outputs']:
    key=('top',pin,None);assert waves[0][key]==reference[key],(name,pin,waves[0][key],reference[key])
 results[name]={'trace':traces[0],'pins':pins,'vcs_compared':bool(a.vcs)}
 if name=='latest':
  lists=w/'lists';lists.mkdir(exist_ok=True)
  (lists/'timing.f').write_text('--sdf-annotate ../delay.sdf\n--gate-models ../cells.v\n--gate-netlist ../net.v\n--gate-top dut\n--liberty ../cells.lib\n../tb.v\n')
  run([compiler,'-F',lists/'timing.f','--wave-support','--emit-only','--emit-cpp',w/'from-list.cpp'],out,'filelist.log')
  assert (w/'from-list.cpp').read_bytes()==(w/'native.dsim.cpp').read_bytes()
  results[name]['list_relative_sdf_identical_cpp']=True
 print('PASS compiled SDF',name,flush=True)


# Unsupported timing never falls back to zero or overwrites a reviewable output.
import shutil,re
w=out/'strict';w.mkdir(exist_ok=True)
for f in ['cells.v','cells.lib','net.v','tb.v','delay.sdf']:shutil.copyfile(out/'latest'/f,w/f)
original_model=(w/'cells.v').read_text();original_sdf=(w/'delay.sdf').read_text()
protected=w/'protected.cpp';report=w/'protected.json';protected.write_text('keep-cpp');report.write_text('keep-ir')
def reject(name,message,extra=()):
 run(command(w)+['--emit-only','--emit-cpp',protected,'--emit-ir',report,*extra],w,name+'.log',False)
 assert message in (w/(name+'.log')).read_text(),name
 assert protected.read_text()=='keep-cpp' and report.read_text()=='keep-ir'
(w/'cells.v').write_text(original_model.replace('(A=>Z)','if(B+1) (A=>Z)'))
(w/'delay.sdf').write_text(original_sdf.replace('(IOPATH A Z (7))','(COND B+1 (IOPATH A Z (7)))'))
reject('conditional-expression','unsupported timing condition')
(w/'cells.v').write_text(original_model.replace('endspecify','$nochange(A,posedge B,1,2);endspecify'))
(w/'delay.sdf').write_text(original_sdf);reject('checks','timing-check execution')
run(command(w)+['--no-timingchecks','--emit-only','--emit-cpp',w/'checks-disabled.cpp'],w,'checks-disabled.log')
(w/'cells.v').write_text(re.sub(r'specify.*?endspecify','specify endspecify',original_model,flags=re.S))
(w/'delay.sdf').write_text(original_sdf.replace('(IOPATH A Z (7))','(DEVICE Z (2))'))
reject('device-without-path','DEVICE output has no module path')
(w/'cells.v').write_text(original_model)
(w/'delay.sdf').write_text(original_sdf);reject('tick','omit --sdf-tick',['--sdf-tick','1ps'])
print('PASS compiled SDF strict unsupported rejection and explicit timing-check opt-out',flush=True)

(out/'results.json').write_text(json.dumps({'status':'PASS','cases':results,'strict_rejections':4,'explicit_checks_disabled':True},indent=2)+'\n')
