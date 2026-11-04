"""Nonzero receiver IOPATH after MIPD, exercising one complete timed chain."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tests/waveform'))
from reader import read,bit_timeline

compiler=Path(sys.argv[1]).resolve()
report=json.loads((Path(sys.argv[2])/'results.json').read_text())
assert report['status']=='PASS'
original=Path(report['run_directory'])/'basic/fanout'
w=Path(tempfile.mkdtemp(prefix='composed-',dir=original.parent.parent))
for name in ['net.v','cells.v','cells.lib','delay.sdf','native-tb.v']:
    shutil.copyfile(original/name,w/name)
models=(w/'cells.v').read_text()
before='module D(input A,output Z);assign Z=A;specify(A=>Z)=0;'
assert models.count(before)==1
(w/'cells.v').write_text(models.replace(before,before.replace('=0;','=5;')))
command=[compiler,'--gate-netlist',w/'net.v','--gate-top','dut','--liberty',w/'cells.lib',
         '--gate-models',w/'cells.v','--sdf-annotate',w/'delay.sdf',w/'native-tb.v',
         '--wave-support','--emit-ir',w/'ir.json','-o',w/'native']
def run(cmd,label):
    p=subprocess.run(list(map(str,cmd)),cwd=w,capture_output=True,text=True,timeout=180)
    (w/(label+'.log')).write_text(p.stdout+p.stderr)
    assert p.returncode==0,(label,p.stderr)
    return p.stdout
run(command,'compile')
streams=[]
for fmt in ['vcd','dwf']:
    run([w/'native','--waveform',w/('native.'+fmt),'--wave-format',fmt],fmt)
    streams.append(bit_timeline(*read(w/('native.'+fmt))))
assert streams[0]==streams[1]
base=bit_timeline(*read(original/'native.vcd'))
for key,changes in base.items():
    if key in [('top','x',None),('top','y',None)]:
        expected=[(t if t==0 and value==(1,1) else t+5,value) for t,value in changes]
        assert streams[0][key]==expected,(key,streams[0][key],expected)
    elif key[-2]=='A':
        assert streams[0][key]==changes
(w/'results.json').write_text(json.dumps(dict(status='PASS',command=list(map(str,command)),
    scope='Actual compiled nonzero5ps receiver IOPATH after per-pin MIPD; output times equal previously VCS-matched receiving-pin trace +5ps. This is a composition check, not a fresh VCS same-design run.'),indent=2)+'\n')
(Path(sys.argv[2])/'composed.json').write_text(json.dumps(dict(status='PASS',directory=str(w)),indent=2)+'\n')
print('PASS compiled INTERCONNECT + nonzero receiver IOPATH + VCD/DWF',w)
