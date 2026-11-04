"""Independent native loops: full state oracle, X fallback and complete VCD streams."""
from pathlib import Path
import json,subprocess,sys
from probe import instrument
ROOT=Path(__file__).resolve().parents[2];compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations
source=Path(__file__).with_name('lanes.sv')
def run(args,work,label):
 p=subprocess.run(list(map(str,args)),cwd=work,capture_output=True,text=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout

def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}

def build(code,work,label,wave=False):
 path=work/(label+'.cpp');path.write_text(code)
 flags=['-I'+config['DSIM_ZSTD_INCLUDE'],config['DSIM_ZSTD_LIBRARY']] if wave else []
 run(['c++','-std=c++17','-O2','-pthread',path,*flags,'-o',work/label],work,label+'-compile')
 return work/label

report={'status':'RUNNING','state_comparisons':0,'captures':0,'fallback_comparisons':0,'partitions':{}}
try:
 for unknown in [False,True]:
  wanted=[]
  for lane,seed in enumerate([1,17,101,999]):
   acc=seed
   for _ in range(3*17):
    acc=(acc*1664525+1013904223)&0xffffffff;acc^=acc>>13
   wanted += [f'STATE {lane*3} {0xffffffff if unknown else acc}:{0xffffffff if unknown else 0}:32',f'STATE {lane*3+1} 3:0:32',f'STATE {lane*3+2} 17:0:32']
  references={}
  for workers in [0,1,2,4]:
   for wave in [False,True]:
    label=('x' if unknown else 'known')+'-'+str(workers)+('-wave' if wave else '')
    work=out/label;work.mkdir(exist_ok=True);cpp=work/'model.cpp';irpath=work/'ir.json'
    flags=(['--threads',str(workers)] if workers else [])+(['--wave-support'] if wave else [])+(['-DDSIM_LANE_UNKNOWN'] if unknown else [])
    run([compiler,source,*flags,'--emit-only','--emit-cpp',cpp,'--emit-ir',irpath],work,'lower')
    code=cpp.read_text();ir=json.loads(irpath.read_text())
    if workers:
     assert ir['parallel']['partitions']==workers;report['partitions'][str(workers)]=workers
    assert '// Native integral loop;' in code
    probe=instrument(code,ir);exe=build(probe,work,'state',wave)
    for mode in (['ordered','settled'] if wave else ['plain']):
     path=work/(mode+'.vcd');path.unlink(missing_ok=True);flags=['--waveform',path,'--wave-format','vcd','--wave-mode',mode] if wave else []
     text=run([exe,*flags],work,mode)
     assert text.splitlines()==wanted,(label,mode,text,wanted);report['state_comparisons']+=1
     if wave:
      data=streams(path)
      if workers==0:references[mode]=data
      else:assert data==references[mode],(label,mode,'complete waveform')
      report['captures']+=1
    if not wave:
     fallback=build(probe.replace('if(s.integral_loop_ready(','if(false && s.integral_loop_ready('),work,'fallback')
     assert run([fallback],work,'fallback-run').splitlines()==wanted;report['fallback_comparisons']+=1
 report['status']='PASS'
except Exception as e:report.update(status='FAIL',error=str(e));raise
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS independent arithmetic:',report)
