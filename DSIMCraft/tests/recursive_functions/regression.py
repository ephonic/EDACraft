from pathlib import Path
import runpy,sys
sys.argv.append("recursive_functions")
runpy.run_path(str(Path(__file__).resolve().parents[1]/"typed_execution.py"),run_name="__main__")
# Deliberately nonterminating recursion must fail with a bounded diagnostic.
import json,os,subprocess
compiler,out=map(lambda p:Path(p).resolve(),sys.argv[1:3])
work=out/'depth';work.mkdir(exist_ok=True)
source=Path(__file__).with_name('depth.sv')
for label,args in [('compile',[compiler,source,'--emit-cpp',work/'model.cpp','-o',work/'sim']),('run',[work/'sim'])]:
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=float(os.environ.get('DSIM_TEST_COMMAND_TIMEOUT','180')))
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==(0 if label=='compile' else 1),(label,p.returncode,p.stderr)
 if label=='run':assert 'recursive function depth exceeds 1024' in p.stderr,p.stderr
p=out/'results.json';report=json.loads(p.read_text());report['runtime_rejections']=1;p.write_text(json.dumps(report,indent=2)+'\n')
