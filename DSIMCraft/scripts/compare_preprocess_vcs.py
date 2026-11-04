#!/usr/bin/env python3
"""Compile identical preprocessing fixtures with dsim and default VCS."""
import argparse,hashlib,json,platform,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests/preprocess'))
from cases import CASES,materialize
from compare_vcs import timed
import subprocess

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dsim',type=Path,default=ROOT/'build/dsim');ap.add_argument('--output',type=Path,default=ROOT/'build/preprocess-vcs');ap.add_argument('--repeat',type=int,default=3);args=ap.parse_args()
    if args.repeat<1:ap.error('repeat must be positive')
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    report=dict(host=platform.node(),dsim_version=subprocess.check_output([args.dsim,'--version'],text=True).strip(),vcs_version=subprocess.check_output(['vcs','-full64','-ID'],text=True,stderr=subprocess.STDOUT),vcs_flags=['-full64','-sverilog','-top','top'],repeat=args.repeat,cases={},note='Correctness fixtures, not performance; flags/undef equivalent explicitly recorded. Same generated input bytes compiled by both tools. No debug_access flag.')
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        for name in CASES:
            w=out/name;w.mkdir(exist_ok=True);case=materialize(w,name)
            row=dict(inputs_sha256={p:hashlib.sha256((w/p).read_bytes()).hexdigest() for p in case['files']},commands={},trace=case['expected']);report['cases'][name]=row;save()
            for tool in ['dsim','vcs']:
                exe=w/(tool+'_simv')
                cmd=[args.dsim.resolve(),*case['args'],'--emit-deps',w/'deps.json','--emit-preprocessed',w/'expanded.v','-o',exe] if tool=='dsim' else ['vcs',*report['vcs_flags'],*case.get('vcs_args',case['args']),'-o',exe]
                row['commands'][tool]=[str(v) for v in cmd]
                if tool=='vcs' and case.get('vcs_failure'):
                    p=subprocess.run(list(map(str,cmd)),cwd=w,text=True,capture_output=True,timeout=180)
                    (w/'vcs-compile.stdout').write_text(p.stdout);(w/'vcs-compile.stderr').write_text(p.stderr)
                    assert p.returncode>0 and case['vcs_failure'] in p.stdout+p.stderr,(name,p.returncode,p.stdout,p.stderr)
                    row['reference_difference']=dict(returncode=p.returncode,diagnostic=case['vcs_difference'])
                    continue
                row[tool+'_compile'],_=timed(cmd,w,tool+'-compile')
                runs=[]
                for i in range(args.repeat):
                    stats,trace=timed([exe],w,f'{tool}-run-{i}');assert trace==case['expected'],(name,tool,trace,case['expected']);runs.append(stats)
                row[tool+'_runs']=runs
            row['status']='KNOWN_REFERENCE_DIFFERENCE' if case.get('vcs_failure') else 'PASS';save();print('PASS VCS/native preprocess',name,flush=True)
    except Exception as e:report['failure']=str(e);raise
    finally:save()
if __name__=='__main__':main()
