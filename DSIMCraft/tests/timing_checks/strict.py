"""Reject unmatched/unsupported check models without overwriting review outputs."""
from pathlib import Path
import argparse,shutil,subprocess
from cases import make
p=argparse.ArgumentParser();p.add_argument('compiler',type=Path);p.add_argument('out',type=Path);a=p.parse_args();out=a.out.resolve();make(out)
w=out/'strict';w.mkdir(exist_ok=True)
for name in ['cells.v','cells.lib','net.v','tb.v','delay.sdf']:shutil.copyfile(out/'hold'/name,w/name)
base=(w/'cells.v').read_text();sdf=(w/'delay.sdf').read_text();cpp=w/'protected.cpp';ir=w/'protected.json';cpp.write_text('keep cpp');ir.write_text('keep ir')
command=[a.compiler.resolve(),'--gate-netlist',w/'net.v','--gate-top','dut','--liberty',w/'cells.lib','--gate-models',w/'cells.v','--sdf-annotate',w/'delay.sdf',w/'tb.v','--emit-only','--emit-cpp',cpp,'--emit-ir',ir]
def reject(name,expected):
 r=subprocess.run(list(map(str,command)),text=True,capture_output=True,timeout=60);(w/(name+'.log')).write_text(r.stdout+r.stderr)
 assert r.returncode and expected in r.stderr,(name,r.stdout,r.stderr)
 assert cpp.read_text()=='keep cpp' and ir.read_text()=='keep ir'
(w/'delay.sdf').write_text(sdf.replace('(HOLD D','(HOLD (posedge D)'))
reject('mismatched-edge','no matching model timing check')
(w/'delay.sdf').write_text(sdf.replace('(HOLD D (posedge C) (5))','(SETUPHOLD D (posedge C) (5) (5))'))
reject('missing-combined-half','no matching model timing check')
(w/'delay.sdf').write_text(sdf)
(w/'cells.v').write_text(base.replace('$hold(posedge C,D,0);','$hold(posedge C,D,0,n);'))
reject('notifier','notifier/extended arguments')
(w/'cells.v').write_text(base.replace('$hold(posedge C,D,0);','$nochange(posedge C,D,0,5);'))
reject('nochange','timing-check execution is not implemented')
print('PASS strict check identity, combined half, notifier/unsupported declaration and protected outputs')
