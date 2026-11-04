#!/usr/bin/env python3
"""Compare native settled digital waveforms with default VCS VCD, same RTL bytes."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from compare_vcs import timed,ROOT
sys.path.insert(0,str(ROOT/'tests/waveform'))
from cases import CASES,EXPECTED
from reader import read,reference_timeline


def digest(timeline):
    return hashlib.sha256(json.dumps(sorted((list(k),v) for k,v in timeline.items()),separators=(',',':')).encode()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dsim',type=Path,default=ROOT/'build/dsim');ap.add_argument('--output',type=Path,default=ROOT/'build/wave-vcs');ap.add_argument('--repeat',type=int,default=3);a=ap.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    report=dict(dsim_version=subprocess.check_output([a.dsim,'--version'],text=True).strip(),vcs_flags=['-full64','-sverilog','-top','top','-top','capture'],repeat=a.repeat,cases={},
                note='Same top.v bytes; VCS auxiliary capture module enables standard VCD, native uses runtime CLI. Compare settled per-tick four-state values and declaration ranges; normalize only optional scalar [0:0]. No performance conclusions from tiny fixtures.')
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        for name,source in CASES.items():
            w=out/name;w.mkdir(exist_ok=True);(w/'top.v').write_text(source)
            (w/'dump.v').write_text('module capture;initial begin $dumpfile("vcs.vcd");$dumpvars(0,top);end endmodule\n')
            row=dict(source_sha256=hashlib.sha256(source.encode()).hexdigest(),dump_sha256=hashlib.sha256((w/'dump.v').read_bytes()).hexdigest(),trace=EXPECTED[name],commands={});report['cases'][name]=row;save()
            native=w/'native';vcs=w/'vcs'
            commands={'native_compile':[a.dsim.resolve(),'--wave-support',w/'top.v','-o',native],
                      'vcs_compile':['vcs',*report['vcs_flags'],'top.v','dump.v','-o',vcs]}
            for key,cmd in commands.items():row['commands'][key]=[str(x) for x in cmd];row[key],_=timed(cmd,w,key)
            common=None
            for tool in ['native','vcs']:
                rows=[]
                for i in range(a.repeat):
                    dest=w/f'{tool}-{i}.vcd';dest.unlink(missing_ok=True)
                    if tool=='native':cmd=[native,'--waveform',dest,'--wave-format','vcd','--wave-mode','settled']
                    else:
                        (w/'vcs.vcd').unlink(missing_ok=True);cmd=[vcs]
                    stats,trace=timed(cmd,w,f'{tool}-run-{i}');assert trace==EXPECTED[name],(name,tool,trace)
                    if tool=='vcs':(w/'vcs.vcd').rename(dest)
                    m,e=read(dest);timeline=reference_timeline(m,e)
                    if common is None:common=timeline
                    assert timeline==common,(name,tool,timeline,common)
                    stats.update(wave_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),timeline_sha256=digest(timeline));rows.append(stats)
                row[tool+'_runs']=rows
            row['timeline_sha256']=digest(common);row['status']='PASS';save();print('PASS native/default VCS waveform',name,flush=True)
    except Exception as e:report['failure']=str(e);raise
    finally:save()


if __name__=='__main__':main()
