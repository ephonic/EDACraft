#!/usr/bin/env python3
"""Run on the VCS host after sourcing /apps/EDAs/syn.bash.

Each tool compiles and runs the same fixtures on this host. Small fixtures validate
semantics; timing/RSS are recorded for reproducibility, not performance claims.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import signal
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('regression', ROOT/'tests/regression.py')
regression = importlib.util.module_from_spec(spec)
spec.loader.exec_module(regression)

def timed(command, work, stem, timeout=180):
    metrics=work/f'{stem}.time'
    start=time.perf_counter()
    p=subprocess.Popen(['/usr/bin/time','-v','-o',str(metrics),*[str(s) for s in command]],
                       cwd=work,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                       start_new_session=True)
    try:
        output,_=p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # Terminate the measured command and compiler children together; killing
        # only /usr/bin/time can otherwise leave a large compile running.
        try: os.killpg(p.pid,signal.SIGTERM)
        except ProcessLookupError: pass
        try: output,_=p.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            try: os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            output,_=p.communicate()
        (work/f'{stem}.log').write_text(output+f'\nTimed out after {timeout}s; process group terminated.\n')
        raise RuntimeError(f'{stem} timed out after {timeout}s (process group terminated)')
    elapsed=time.perf_counter()-start
    (work/f'{stem}.log').write_text(output)
    if p.returncode:
        raise RuntimeError(f'{stem} failed ({p.returncode}):\n{output}')
    rss=re.search(r'Maximum resident set size \(kbytes\): (\d+)',metrics.read_text())
    return {'wall_seconds':elapsed,'peak_rss_kb':int(rss[1]) if rss else None}, regression.traces(output)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dsim',type=Path,default=ROOT/'build/dsim')
    ap.add_argument('--output',type=Path,default=ROOT/'build/vcs-comparison')
    ap.add_argument('--repeat',type=int,default=3)
    ap.add_argument('--case',action='append',choices=list(regression.CASES),help='Only compare named cases; repeatable')
    ap.add_argument('--vcs-flag',action='append',default=[],help='Extra VCS compile flag; use --vcs-flag=-flag (recorded in report)')
    args=ap.parse_args()
    if args.repeat<1: ap.error('--repeat must be positive')
    out=args.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    version=subprocess.run(['vcs','-full64','-ID'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=30)
    (out/'vcs-version.log').write_text(version.stdout)
    if version.returncode: raise RuntimeError(version.stdout)
    report={'host':platform.node(),'platform':platform.platform(),
            'dsim_version':subprocess.check_output([str(args.dsim.resolve()),'--version'],text=True).strip(),
            'vcs_version':version.stdout,'cxx_version':subprocess.check_output(['c++','--version'],text=True),
            'vcs_flags':['-full64','-sverilog','-top','top',*args.vcs_flag],
            'dsim_flags':['--top','top'],'native_flags':['-std=c++17','-O2'],
            'repeat':args.repeat,'note':'Tiny correctness fixtures; timings do not establish relative simulator performance.',
            'cases':{}}
    # Save partial results after every case so an external failure is visible.
    try:
        for name,expected in regression.CASES.items():
            if args.case and name not in args.case: continue
            work=out/name; work.mkdir(exist_ok=True)
            source=ROOT/'tests/cases'/f'{name}.v'
            native=work/'dsim_simv'; vcs=work/'vcs_simv'
            record={'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
            record['dsim_compile'],_=timed([args.dsim.resolve(),'--top','top',source,'-o',native],work,'dsim-compile')
            record['vcs_compile'],_=timed(['vcs',*report['vcs_flags'],source,'-o',vcs],work,'vcs-compile')
            for tool,exe in [('dsim',native),('vcs',vcs)]:
                runs=[]
                for i in range(args.repeat):
                    stats,trace=timed([exe],work,f'{tool}-run-{i}')
                    if trace!=expected: raise AssertionError(f'{name} {tool}: expected {expected}, got {trace}')
                    runs.append(stats)
                record[f'{tool}_runs']=runs
                record[f'{tool}_median_seconds']=statistics.median(r['wall_seconds'] for r in runs)
            record['trace']=expected; record['status']='PASS'; report['cases'][name]=record
            (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
            print(f'PASS VCS/dsim {name}',flush=True)
    except Exception as e:
        report['failure']=str(e)
        raise
    finally:
        (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__': main()
