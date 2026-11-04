"""Replay unchanged retained memory against the qualified complete four-state reference."""
from pathlib import Path
import hashlib,json,os,signal,shutil,subprocess,sys,time
fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
ROOT=fixtures.parents[1];sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
sha=lambda data:hashlib.sha256(data).hexdigest()
report=dict(status='RUNNING',binary_sha256=sha(compiler.read_bytes()),models={},captures=0)
def run(args,work,label):
 start=time.monotonic()
 with (work/(label+'.stdout')).open('w') as stdout,(work/(label+'.stderr')).open('w') as stderr:
  p=subprocess.Popen(list(map(str,args)),cwd=work,stdout=stdout,stderr=stderr,start_new_session=True)
  try:code=p.wait(timeout=180)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGKILL);p.wait();raise AssertionError((label,'original 180 second budget exceeded'))
 assert code==0,(label,code,(work/(label+'.stderr')).read_text()[-2500:])
 return (work/(label+'.stdout')).read_text(),time.monotonic()-start
try:
 for name,row in json.loads((fixtures/'inventory.json').read_text()).items():
  work=out/name;work.mkdir(exist_ok=True)
  for f in row['files']:
   assert sha((fixtures/name/f).read_bytes())==row['input_sha256'][f],(name,f)
   (work/f).parent.mkdir(exist_ok=True,parents=True);shutil.copyfile(fixtures/name/f,work/f)
  _,seconds=run([compiler,'--timescale','1ns/1ps','--top','tb_compare',*[f for f in row['files'] if f.endswith('.sv')],'--emit-cpp','model.cpp','-o','simv'],work,'compile')
  text,runtime=run([work/'simv'],work,'run');lines=[]
  for line in text.splitlines():
   if line.startswith('RTL_DUAL_TRACE_H4 '):
    fields=line.split();assert len(fields)==len(row['outputs'])+2;words=[]
    for token,(key,width) in zip(fields[2:],row['outputs']):
     assert token.startswith(key+'=') and len(token.split('=',1)[1])==(width+1)//2
     raw=int(token.split('=',1)[1],16);assert raw>>(2*width)==0
     words.append(key+'='+''.join('01xz'[(raw>>(2*i))&3] for i in reversed(range(width))))
    lines.append('RTL_DUAL_TRACE '+fields[1]+' '+' '.join(words))
   elif line.startswith(('RTL_DUAL_TRACE ','RTL_DUAL_DONE ')):lines.append(line)
  assert len(lines)==row['events']+1,(name,'complete ordered history required')
  for i,line in enumerate(lines[:-1]):
   fields=line.split();assert fields[:2]==['RTL_DUAL_TRACE',str(i)],(name,i,'order')
   assert len(fields)==len(row['outputs'])+2,(name,i,'inventory')
   for token,(key,width) in zip(fields[2:],row['outputs']):
    assert token.startswith(key+'=') and len(token)==len(key)+1+width and set(token[len(key)+1:])<=set('01xz'),(name,i,key,'full four-state width')
  assert lines[-1]=='RTL_DUAL_DONE events='+str(row['events'])+' outputs='+str(len(row['outputs'])),name
  digest=sha(('\n'.join(lines)+'\n').encode())
  assert digest==row['expected_trace_sha256'],(name,'qualified VCS complete history mismatch')
  report['models'][name]=dict(status='PASS',events=row['events'],outputs=len(row['outputs']),compile_seconds=round(seconds,3),run_seconds=round(runtime,3),trace_sha256=digest,input_sha256=row['input_sha256'])
  print('PASS function boundary original',name,row['events'],'events',flush=True)
 # Function call arguments, four-state case matching and body side effects.
 refs={}
 expected=(fixtures/'semantics.expected.txt').read_text()
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  work=out/('semantics-'+backend);work.mkdir(exist_ok=True)
  run([compiler,fixtures/'semantics.sv',*flags,'--wave-support','--emit-cpp','model.cpp','-o','simv'],work,'compile')
  for mode in ['ordered','settled']:
   for fmt,extra in [('vcd',[]),('dwf',[]),('async.dwf',['--wave-async'])]:
    wave=work/(mode+'.'+fmt);wave.unlink(missing_ok=True)
    text,_=run([work/'simv','--waveform',wave,'--wave-format','vcd' if fmt=='vcd' else 'dwf','--wave-mode',mode,*extra],work,mode+'-'+fmt)
    assert text==expected,(backend,text,expected)
    meta,events=read(wave);values=[[] for _ in meta['signals']]
    for tick,kind,payload in events:
     if kind=='value':values[payload[0]].append((tick,payload[1]))
    streams={key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
    if backend=='serial' and fmt=='vcd':refs[mode]=streams
    assert streams==refs[mode],(backend,mode,fmt)
    if fmt=='async.dwf':assert wave.read_bytes()==(work/(mode+'.dwf')).read_bytes()
    report['captures']+=1
 # Both wave-enabled kernels and the non-wave parallel CLI start without an
 # implicit 10M-instruction cap. An explicit budget remains enforced.
 for backend,flags in [('serial',[]),('parallel',['--threads','2'])]:
  work=out/('budget-'+backend);work.mkdir(exist_ok=True)
  for wave_support in [False,True]:
   label='wave' if wave_support else 'plain'
   run([compiler,fixtures/'budget.sv',*flags,*(['--wave-support'] if wave_support else []),'-o',label],work,label+'-compile')
   args=[work/label]
   if backend=='parallel':args+=['--parallel-stats']
   if wave_support:
    wave=work/'budget.dwf';wave.unlink(missing_ok=True);args+=['--waveform',wave,'--wave-async']
   run(args,work,label+'-run')
   if backend=='parallel':assert '"partitions":2' in (work/(label+'-run.stderr')).read_text()
   if wave_support:
    lanes=timeline(*read(wave));assert lanes[('top','one')][2][-1][1]==(7,0) and lanes[('top','two')][2][-1][1]==(9,0)
    report['captures']+=1
   p=subprocess.run([work/label,'--max-events','1000'],cwd=work,capture_output=True,text=True,timeout=30)
   (work/(label+'-bounded.stderr')).write_text(p.stderr)
   assert p.returncode==1 and 'execution budget exhausted' in p.stderr
 # The default budget must permit a valid >10M-step run, while an explicit
 # user budget still interrupts and reports failure.
 work=out/'retained_memory_codec'
 q=subprocess.run([work/'simv','--max-events','1000'],cwd=work,capture_output=True,text=True,timeout=30)
 (work/'bounded.stdout').write_text(q.stdout);(work/'bounded.stderr').write_text(q.stderr)
 assert q.returncode==1 and 'execution budget exhausted' in q.stderr
 report.update(status='PASS',events=sum(r['events'] for r in report['models'].values()),explicit_budget_rejection=True)
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
