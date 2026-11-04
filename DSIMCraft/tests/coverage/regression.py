"""Coverage hits, lexical receivers, scheduled samples and checkpoint ownership."""
from pathlib import Path
import json,runpy,sys
sys.argv.append('coverage')
state=runpy.run_path(str(Path(__file__).resolve().parents[1]/'typed_execution.py'),run_name='__main__')
root,compiler,out,run,report=(state[key] for key in ('root','compiler','out','run','report'))
run([compiler,root/'tests/coverage/clones.sv','--threads','2','--emit-only','--emit-cpp',out/'domains.cpp','--emit-ir',out/'domains.json'],out,'domains')
assert json.loads((out/'domains.json').read_text())['parallel']['partitions']==1
for name,case in json.loads((root/'tests/coverage/runtime_errors.json').read_text()).items():
    work=out/('runtime-'+name);work.mkdir(exist_ok=True)
    source=work/'model.sv';source.write_text(case['body']+'\n')
    run([compiler,source,'-o',work/'model'],work,'compile')
    run([work/'model'],work,'run',False)
    assert case['diagnostic'] in (work/'run.stderr').read_text(),name
report['runtime_errors']=len(json.loads((root/'tests/coverage/runtime_errors.json').read_text()))
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
