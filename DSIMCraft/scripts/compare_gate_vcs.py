#!/usr/bin/env python3
"""Same-host VCS differential checks for the independent gate frontend."""
import argparse,hashlib,json,platform,subprocess,sys
from pathlib import Path
from compare_vcs import ROOT,timed
sys.path.insert(0,str(ROOT/'tests/gate'))
from regression import CASES,command,library,reference_models


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dsim',type=Path,default=ROOT/'build/dsim')
    ap.add_argument('--output',type=Path,default=ROOT/'build/vcs-gate')
    ap.add_argument('--repeat',type=int,default=3)
    ap.add_argument('--case',action='append',choices=CASES)
    args=ap.parse_args()
    if args.repeat<1: ap.error('repeat must be positive')
    out=args.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    fixtures=ROOT/'tests/gate'
    report={'host':platform.node(),'platform':platform.platform(),
            'dsim_version':subprocess.check_output([args.dsim.resolve(),'--version'],text=True).strip(),
            'vcs_version':subprocess.check_output(['vcs','-full64','-ID'],text=True,stderr=subprocess.STDOUT),
            'vcs_flags':['-full64','-sverilog','-top','top'],'repeat':args.repeat,
            'cxx_version':subprocess.check_output(['c++','--version'],text=True),'native_flags':['-std=c++17','-O2'],
            'note':'Structural source is parsed by the independent gate Network frontend. VCS uses the same netlist/TB plus independent functional Verilog cell models. Ideal-power, zero-delay simulation only.',
            'cases':{}}
    try:
        for case in args.case or CASES:
            work=out/case; work.mkdir(exist_ok=True)
            inputs=[fixtures/(case+'.net.v'),fixtures/(case+'.tb.v'),library(case),reference_models(case)]
            expected=json.loads((fixtures/(case+'.expected.json')).read_text())
            record={'inputs_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},'trace':expected}
            report['cases'][case]=record
            native,vcs=work/'dsim_simv',work/'vcs_simv'
            native_cmd=command(args.dsim.resolve(),case)+['--emit-ir',work/'ir.json','-o',native]
            vcs_cmd=['vcs','-full64','-sverilog','-top','top',inputs[0],inputs[1],inputs[3],'-o',vcs]
            record['compile_commands']={k:[str(a) for a in c] for k,c in [('dsim',native_cmd),('vcs',vcs_cmd)]}
            record['dsim_compile'],_=timed(native_cmd,work,'dsim-compile')
            record['vcs_compile'],_=timed(vcs_cmd,work,'vcs-compile')
            for tool,exe in [('dsim',native),('vcs',vcs)]:
                record[tool+'_runs']=[]
                for i in range(args.repeat):
                    stats,trace=timed([exe],work,f'{tool}-run-{i}')
                    if trace!=expected: raise AssertionError(f'{case} {tool}: {trace} != {expected}')
                    record[tool+'_runs'].append(stats)
            record['status']='PASS'; print('PASS VCS/gate',case,flush=True)
    except Exception as e:
        report['failure']=str(e); raise
    finally:
        (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__': main()
