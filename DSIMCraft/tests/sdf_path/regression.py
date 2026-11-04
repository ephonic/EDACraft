from pathlib import Path
import hashlib,json,subprocess,sys,tempfile
HERE=Path(__file__).resolve().parent;probe=Path(sys.argv[1]).resolve()
record=dict(status='RUNNING',binary_sha256=hashlib.sha256(probe.read_bytes()).hexdigest(),cases={},failures=[])
for row in json.loads((HERE/'oracles.json').read_text())['cases']:
    sdf=HERE/row['sdf'];assert hashlib.sha256(sdf.read_bytes()).hexdigest()==row['input_sha256']
    cmd=[str(probe),str(HERE),str(sdf),row['scale'],row['base']];runs=[]
    for i in range(3):
        r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);runs.append(dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
        if row.get('unsupported'):
            valid=r.returncode!=0 and not r.stdout and 'unsupported VCS readback' in r.stderr
        else:valid=r.returncode==0 and r.stdout.splitlines()==row['expected']
        if not valid:record['failures'].append(dict(case=row['name'],run=i,expected=row['expected'],actual=r.stdout.splitlines(),stderr=r.stderr))
    record['cases'][row['name']]=dict(command=cmd,runs=runs)
# Unsupported objects fail before constructing/running the simulator, including
# errors after a valid update. This adapter must never silently ignore syntax.
with tempfile.TemporaryDirectory(prefix='dsim-sdf-probe-') as temporary:
    sdf=Path(temporary)/'unsupported.sdf'
    for entry in ['(COND A (IOPATH A Z (1)))','(IOPATH (posedge A) Z (1))','(IOPATH A Z ((1)(2)))','(IOPATH BAD Z (1))','(IOPATH A Z (1e80))']:
        sdf.write_text('(DELAYFILE (SDFVERSION "3.0") (TIMESCALE 1ns) (CELL (CELLTYPE "B") (INSTANCE) (DELAY (ABSOLUTE (IOPATH A Z (1)) '+entry+'))))')
        r=subprocess.run([str(probe),str(HERE),str(sdf),'1ns/1ps','0'],capture_output=True,text=True)
        assert r.returncode!=0 and not r.stdout,(entry,r.stdout,r.stderr)
record['status']='FAIL' if record['failures'] else 'PASS'
for failure in record['failures'][::3]:print('MISMATCH',failure['case'],failure['actual'],failure['stderr'])
unsupported=sum(bool(r.get('unsupported')) for r in json.loads((HERE/'oracles.json').read_text())['cases'])
record['supported_cases']=len(record['cases'])-unsupported;record['unsupported_rejections']=unsupported
if len(sys.argv)>2:Path(sys.argv[2]).write_text(json.dumps(record,indent=2)+'\n')
print(record['status'],len(record['cases'])-unsupported,'supported cases,',unsupported,'explicit unsupported rejections; three native runs each')
sys.exit(bool(record['failures']))
