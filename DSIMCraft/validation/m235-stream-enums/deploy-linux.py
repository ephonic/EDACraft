"""Stage a frozen Intel build; do not replace an entry upgraded while building."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
root,build,prefix,out=map(lambda p:Path(p).resolve(),sys.argv[1:5]);out.mkdir(parents=True,exist_ok=True)
previous={str(p):os.readlink(p) for p in [prefix/'bin/dsim',prefix/'dsim']};previous_binary=(prefix/'bin/dsim').resolve()
state=out/'status.json'
def save(status,**fields):state.write_text(json.dumps(dict(status=status,**fields),indent=2)+'\n')
def run(command,label,cwd=root):
 with (out/(label+'.stdout')).open('w') as a,(out/(label+'.stderr')).open('w') as e:p=subprocess.run(list(map(str,command)),cwd=cwd,stdout=a,stderr=e,timeout=14400)
 assert not p.returncode,(label,p.returncode)
def link(path,target):
 tmp=path.parent/('.m235-'+str(os.getpid()));tmp.unlink(missing_ok=True);os.symlink(os.path.relpath(target,path.parent),tmp);os.replace(tmp,path)
try:
 save('BUILDING',previous=str(previous_binary));before=set((prefix/'releases').iterdir())
 run(['cmake','-S',root,'-B',build,'-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER=/opt/intel/oneapi/compiler/2026.1/bin/icpx','-DDSIM_MODEL_CXX=/opt/intel/oneapi/compiler/2026.1/bin/icpx','-DDSIM_Z3_INCLUDE=/apps/EDAs/own/dsim/deps/z3-4.15.4/include','-DDSIM_Z3_LIBRARY=/apps/EDAs/own/dsim/deps/z3-4.15.4/lib/libz3.a','-DTCL_INCLUDE_PATH=/apps/anaconda3/include','-DTCL_LIBRARY=/usr/lib64/libtcl8.6.so'],'configure')
 run([sys.executable,root/'scripts/publish_stable.py','--build',build,'--prefix',prefix,'--stage-only','--check-group','virtual_interfaces','--check-group','stream_targets','--check-group','stream_enum_casts','--check-group','interfaces','--check-jobs','3','--command-timeout','10800'],'publish')
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
 matches=[p for p in set((prefix/'releases').iterdir())-before if (p/'release.json').exists() and json.loads((p/'release.json').read_text())['git_commit']==commit]
 assert len(matches)==1,matches
 release=matches[0];receipt=json.loads((release/'release.json').read_text());assert receipt['status']=='PASS' and not receipt['git_dirty'] and not receipt['active']
 if (prefix/'bin/dsim').resolve()!=previous_binary:
  save('SUPERSEDED',release=str(release));sys.exit(0)
 for entry in previous:link(Path(entry),release/'dsim')
 try:
  receipt['active']=True;(release/'release.json').write_text(json.dumps(receipt,indent=2)+'\n')
  run([sys.executable,root/'validation/m235-stream-enums/check-entry.py',root,prefix/'bin/dsim',out/'entry'],'actual-entry')
  for entry in previous:
   assert Path(entry).resolve()==release/'dsim'
   run([entry,'--help'],'alias-'+str(len(entry)))
  save('ACTIVE',release=str(release),source_commit=commit)
 except BaseException:
  receipt['active']=False;(release/'release.json').write_text(json.dumps(receipt,indent=2)+'\n')
  for entry,target in previous.items():
   path=Path(entry)
   if path.resolve()==release/'dsim':
    tmp=path.parent/('.m235-rollback-'+str(os.getpid()));os.symlink(target,tmp);os.replace(tmp,path)
  raise
except BaseException as error:
 if not isinstance(error,SystemExit) or error.code:save('FAIL',error=str(error));raise
