"""Actual generated checks: annotation, diagnostics, waveforms and optional VCS."""
from pathlib import Path
import argparse,json,re,subprocess,sys
from cases import make
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tests/waveform'))
from reader import read
p=argparse.ArgumentParser();p.add_argument('compiler',type=Path);p.add_argument('out',type=Path);p.add_argument('--vcs',action='store_true');p.add_argument('--reference',type=Path);p.add_argument('--cases',nargs='+');a=p.parse_args()
compiler=a.compiler.resolve();out=a.out.resolve();cases=make(out);cases={k:v for k,v in cases.items() if not a.cases or k in a.cases};assert cases;results={}
def run(command,w,log):
 r=subprocess.run(list(map(str,command)),cwd=w,text=True,capture_output=True,timeout=180)
 (w/log).write_text(r.stdout+r.stderr);assert r.returncode==0,(command,r.stdout,r.stderr)
 assert 'runtime error:' not in r.stderr and 'AddressSanitizer' not in r.stderr
 return r.stdout
for name,c in cases.items():
 row=dict(status='RUNNING')
 try:
  w=out/name
  run([compiler,'--gate-netlist',w/'net.v','--gate-top','dut','--liberty',w/'cells.lib','--gate-models',w/'cells.v','--sdf-annotate',w/'delay.sdf',w/'tb.v','--wave-support','--emit-ir',w/'ir.json','-o',w/'native'],w,'native-compile.log')
  outputs=[];waves=[]
  for mode in ['none','vcd','dwf']:
   command=[w/'native']
   if mode!='none':
    dest=w/('native.'+mode);dest.unlink(missing_ok=True)
    command+=['--waveform',dest,'--wave-format',mode,'--wave-block-events','7']
   outputs.append(run(command,w,'native-'+mode+'.log'))
   if mode!='none':waves.append(read(w/('native.'+mode)))
  assert all(text==outputs[0] for text in outputs),name
  assert waves[0]==waves[1],(name,'wave mismatch')
  native=[(k,int(t)) for k,t in re.findall(r'^TIMING kind=(\w+) time=(\d+)',outputs[0],re.M)]
  row=dict(status='PASS',violations=native,trace=[x for x in outputs[0].splitlines() if x.startswith('TRACE ')],ir=json.loads((w/'ir.json').read_text())['gate_design'])
  if a.vcs:
   run(['vcs','-full64','-sverilog','+define+VCS_REFERENCE','-top','top',w/'cells.v',w/'net.v',w/'tb.v','-o',w/'vcs'],w,'vcs-compile.log')
   text=run([w/'vcs','-no_save'],w,'vcs-run.log')
  if a.reference:
   ref=a.reference.resolve()/name
   for f in ['cells.v','cells.lib','net.v','delay.sdf','tb.v']:assert (w/f).read_bytes()==(ref/f).read_bytes(),(name,f)
   text=(ref/'vcs-run.log').read_text();(w/'vcs-reference.log').write_text(text)
  if a.vcs or a.reference:
   notifier=[(k,int(t)) for k,t in re.findall(r'^CHECK kind=(\w+) time=(\d+)',text,re.M)]
   reference=[]
   for match in re.finditer(r'Timing violation[^\n]*\n\s*\$(\w+)\((.*?)\);',text,re.S):
    events=re.findall(r':\s*(\d+)',match[2].split('limit')[0]);assert events,(name,match[0])
    reference.append((match[1].upper(),max(map(int,events))))
   row['vcs_notifier_observations']=notifier
   assert len(reference)==text.count('Timing violation'),(name,'unparsed VCS diagnostic')
   row.update(vcs_violations=reference,vcs_comparison='PASS' if reference==native else 'FAIL')
   row['annotation']=((a.reference.resolve()/name if a.reference else w)/'annotation.log').read_text()
   counts=tuple(int(re.search(r'Total '+label+r':\s*(\d+)',row['annotation'])[1]) for label in ['errors','warnings'])
   row['vcs_annotation_counts']=dict(errors=counts[0],warnings=counts[1])
   assert counts==((1,0) if name=='negative' else (0,0)),(name,row['annotation'])
   if name=='negative':assert 'SDFCOM_NNTC' in row['annotation'] and 'replaced by 0' in row['annotation'] and row['ir']['negative_check_limits_clamped']==1
   assert row['trace']==[x for x in text.splitlines() if x.startswith('TRACE ')],name
   if reference!=native:
    row['status']='FAIL';results[name]=row
    (out/'results.json').write_text(json.dumps(dict(status='FAIL',cases=results),indent=2)+'\n')
    raise AssertionError((name,native,reference))
  expected=root/'tests/timing_checks/expected.json'
  if expected.exists():assert native==[tuple(x) for x in json.loads(expected.read_text())[name]],(name,native,'frozen VCS reference')
  results[name]=row;print('PASS checks',name,native,flush=True)
 except Exception as exc:
  row.update(status='FAIL',error=str(exc));results[name]=row;print('FAIL checks',name,str(exc),flush=True)
(out/'results.json').write_text(json.dumps(dict(status='PASS' if all(c['status']=='PASS' for c in results.values()) else 'FAIL',cases=results),indent=2)+'\n')
if any(c['status']!='PASS' for c in results.values()):raise SystemExit(1)
