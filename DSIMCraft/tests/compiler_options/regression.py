"""Literal compiler argv, real optimized compilation and atomic failed output."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
source=Path(__file__).with_name('input.sv');exe=out/'program';record=out/'argv.json'
cache=Path(sys.argv[3]) if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
default_opt=config.get('DSIM_MODEL_OPTIMIZATION','-O2')
def run(args,label,good=True):
 p=subprocess.run(list(map(str,args)),cwd=out,capture_output=True,text=True,timeout=180)
 (out/(label+'.stdout')).write_text(p.stdout);(out/(label+'.stderr')).write_text(p.stderr)
 assert (p.returncode==0)==good,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout
wrapper=out/'compiler with spaces';real=shutil.which('c++');assert real
wrapper.write_text('#!'+sys.executable+'\nimport os,sys,json\nfrom pathlib import Path\nPath('+repr(str(record))+').write_text(json.dumps(sys.argv[1:]))\nos.execv('+repr(real)+',['+repr(real)+']+sys.argv[1:])\n');wrapper.chmod(0o755)
literal='-DDSIM_LITERAL=unused with spaces;$(touch NEVER_EXECUTE)'
flags=['--cxx',wrapper,'--cxx-flag','-O3','--cxx-flag',literal]
run([compiler,source,*flags,'-o',exe],'optimized-compile')
argv=json.loads(record.read_text());assert argv[0:4]==['-std=c++17',default_opt,'-O3',literal],argv
assert not (out/'NEVER_EXECUTE').exists();assert run([exe],'optimized-run').splitlines()==['TRACE compiler flags          17']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=sha(exe)
run([compiler,source,'--cxx',wrapper,'--cxx-flag','-fno-such-dsim-option','-o',exe],'failed-compile',False)
assert sha(exe)==before and not list(out.glob('program.tmp.*'))
for label,args in [('missing',['--cxx-flag']),('empty',['--cxx-flag',''])]:
 run([compiler,source,*args,'-o',exe],label,False);assert sha(exe)==before
run([compiler,source,'--cxx',wrapper,'-o',exe],'default-compile')
argv=json.loads(record.read_text());assert argv[:2]==['-std=c++17',default_opt] and literal not in argv and argv.count('-O3')==int(default_opt=='-O3')
assert run([exe],'default-run')==run([exe],'after-failed-run')
intel_wrapper=out/'icpx'
intel_wrapper.write_text('#!'+sys.executable+'\nimport os,sys,json\nfrom pathlib import Path\nPath('+repr(str(record))+').write_text(json.dumps(sys.argv[1:]))\nargs=[a for a in sys.argv[1:] if a!="-fp-model=strict"]\nos.execv('+repr(real)+',['+repr(real)+']+args)\n');intel_wrapper.chmod(0o755)
run([compiler,source,'--cxx',intel_wrapper,'--cxx-flag','-fno-fast-math','-o',exe],'intel-argv')
argv=json.loads(record.read_text());assert argv[:4]==['-std=c++17',default_opt,'-fp-model=strict','-fno-fast-math'],argv
assert run([exe],'intel-argv-run').splitlines()==['TRACE compiler flags          17']
run([compiler,source,'-o',exe],'configured-compiler')
assert run([exe],'configured-compiler-run').splitlines()==['TRACE compiler flags          17']
(out/'results.json').write_text(json.dumps({'status':'PASS','literal_argument':literal,'failed_compile_preserves_binary':True,'default_flags':['-std=c++17',default_opt]},indent=2)+'\n')
print('PASS compiler flags: exact argv, spaces, metacharacters, O3 execution, configured default, atomic failure')
