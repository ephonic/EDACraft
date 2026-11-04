#!/usr/bin/env python3
"""Default VCS timing differential: exact input hashes, raw logs, repeated TRACE."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from compare_vcs import timed,ROOT
sys.path.insert(0,str(ROOT/'tests/time'))
from cases import CASES

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--dsim',type=Path,default=ROOT/'build/dsim');ap.add_argument('--output',type=Path,default=ROOT/'build/time-vcs');ap.add_argument('--repeat',type=int,default=3);ap.add_argument('--case',action='append',choices=sorted(CASES));a=ap.parse_args()
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 report=dict(dsim_version=subprocess.check_output([a.dsim,'--version'],text=True).strip(),vcs_flags=['-full64','-sverilog','-top','top'],repeat=a.repeat,cases={},note='Default optimization. resetall requires explicit -timescale=1s/1s because VCS rejects mixed declared/undeclared timescales after resetall; retain the original NTSFM failure separately.')
 def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
 try:
  for name,(source,expected) in CASES.items():
   if a.case and name not in a.case:continue
   w=out/name;w.mkdir(exist_ok=True);(w/'top.v').write_text(source)
   flags=report['vcs_flags']+(['-timescale=1s/1s'] if name=='resetall' else [])
   row=dict(vcs_flags=flags,source_sha256=hashlib.sha256(source.encode()).hexdigest(),expected=expected,commands={});report['cases'][name]=row;save()
   for tool in ['native','vcs']:
    binary=w/tool
    cmd=[a.dsim.resolve(),w/'top.v','-o',binary] if tool=='native' else ['vcs',*flags,'top.v','-o',binary]
    row['commands'][tool]=list(map(str,cmd));row[tool+'_compile'],_=timed(cmd,w,tool+'-compile')
    runs=[]
    for i in range(a.repeat):
     stats,trace=timed([binary],w,f'{tool}-{i}');assert trace==expected,(name,tool,trace,expected);runs.append(stats)
    row[tool+'_runs']=runs
   row['status']='PASS';save();print('PASS native/VCS timing',name,flush=True)
 except Exception as error:report['failure']=str(error);raise
 finally:save()
if __name__=='__main__':main()
