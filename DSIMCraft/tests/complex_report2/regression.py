"""REPORT2 originals plus signed-expression and reproducible RNG checks."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations,timeline
cache_path=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
cache={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache_path.read_text().splitlines() if '=' in x and not x.startswith('//')}
def run(cmd,work,label,ok=True):
 p=subprocess.run(list(map(str,cmd)),cwd=work,text=True,capture_output=True,timeout=300)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert (p.returncode==0)==ok and p.returncode>=0,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout
def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
report={'status':'RUNNING','probes':{},'designs':{},'captures':0,'rollbacks':0}
try:
 for name,digest in json.loads((fixtures/'original-sources.json').read_text())['files'].items():
  assert hashlib.sha256((fixtures/name).read_bytes()).hexdigest()==digest,name
 for name in ['pipecpu','axi4','cache','spi']:
  work=out/name;work.mkdir(exist_ok=True)
  for file in (fixtures/name).iterdir():
   if file.is_file():shutil.copyfile(file,work/file.name)
  run([compiler,'--top','tb','rtl.sv','tb.sv','-o',work/'simv'],work,'compile')
  text=run([work/'simv'],work,'run')
  assert 'ALL PASS' in text and 'FAIL' not in text and 'MISMATCH' not in text,(name,text)
  # Repeating a compiled model must reproduce the full random-driven run.
  assert run([work/'simv'],work,'repeat-run')==text,(name,'run reproducibility')
  report['designs'][name]={'status':'PASS','stdout':text};print('PASS REPORT2 design',name,flush=True)
 for name in ['p21_sra_cond','shift_context','reproducible']:
  work=out/name;work.mkdir(exist_ok=True)
  source=fixtures/'probes2/p21_sra_cond.sv' if name.startswith('p21') else fixtures/'extended'/(name+'.sv')
  top='tb' if name.startswith('p21') else 'top';reference=None;trace=None
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,source,'--top',top,*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
   wave=work/(backend+'.vcd');wave.unlink(missing_ok=True)
   text=run([work/backend,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,backend+'-run')
   if name.startswith('p21'):
    assert text.splitlines()[0]=='direct=ffffffff cond=ffffffff tern=003fffff func=ffffffff ifelse=ffffffff (want ffffffff)',text
   elif name=='shift_context':
    assert text.splitlines()==json.loads((fixtures/'extended/shift-expected.json').read_text()),text
   else:
    assert text.count('TRACE default')==4 and 'TRACE second' in text and 'TRACE explicit reseed pass' in text,text
   current=stream(wave)
   if reference is None:reference=current;trace=text
   else:assert current==reference and text==trace,(name,backend,'complete output/ordered stream')
   report['captures']+=1
  # Compile identical bytes under a different source/output path. The default
  # process RNG stream must be independent of paths and build invocations.
  if name=='reproducible':
   copied=work/'identical-copy.sv';shutil.copyfile(source,copied)
   run([compiler,copied,'--top',top,'-o',work/'recompiled'],work,'recompile')
   assert run([work/'recompiled'],work,'recompiled-run')==trace,'RNG changed across identical-source compilation'
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
s.run_until(0);
if(s.predict_until(100000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
  run(['c++','-std=c++17','-O2','-pthread','-I'+cache['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',cache['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  wave=work/'replay.vcd';wave.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,'replay-run')==trace
  assert stream(wave)==reference,(name,'rollback output/wave');report['captures']+=1;report['rollbacks']+=1
  if name.startswith('p21'):report['probes']['p21_sra_cond']='PASS (tern=003fffff matches VCS)'
  print('PASS REPORT2 semantics',name,flush=True)
 work=out/'probes2';work.mkdir(exist_ok=True)
 for file in (fixtures/'probes2').rglob('*'):
  if file.is_file():
   target=work/file.relative_to(fixtures/'probes2');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
 for name,top,marker,flags in [
  ('p22_varidx_nba','tb','PROBE_VARRD: ok',[]),
  ('p23_multi_always','tb','second always fired',[]),
  ('p25_cli_inc','top','CLI_PROBE: ok W_INC=42',['+incdir+inc','+define+DEF_SET']),
 ]:
  run([compiler,name+'.sv','--top',top,*flags,'-o',work/name],work,name+'-compile')
  text=run([work/name],work,name+'-run');assert marker in text,(name,text);report['probes'][name]='PASS'
 run([compiler,'-f','flist.f','--top','top','+incdir+inc','+define+DEF_SET','-o',work/'flist'],work,'flist-compile')
 assert 'CLI_PROBE: ok W_INC=42' in run([work/'flist'],work,'flist-run');report['probes']['p25_flist']='PASS'
 run([compiler,'p24_vcd.sv','--top','top','--wave-support','-o',work/'vcd'],work,'vcd-compile')
 wave=work/'counter.vcd';wave.unlink(missing_ok=True)
 assert 'VCD_PROBE: cnt=9' in run([work/'vcd','--waveform',wave],work,'vcd-run')
 assert wave.read_bytes().startswith(b'$version') and read(wave)[0]['signals']
 run([work/'vcd','--waveform',wave],work,'overwrite',False);assert 'exist' in (work/'overwrite.stderr').read_text()
 report['probes']['p24_vcd_text']='PASS'
 summary=json.loads(run([compiler,'--sdf-check','timing.sdf'],work,'sdf-check'))
 assert summary['cells']==4 and summary['entries']==7 and summary['kinds']['IOPATH']==7
 report['probes']['p26_sdf_check']='PASS'
 gate=['--gate-netlist','netlist.v','--gate-top','top','--gate-models','models.v','--liberty','cells.lib']
 binding=json.loads(run([compiler,'--sdf-bind-check','timing.sdf',*gate,'--sdf-tick','1ps'],work,'sdf-bind'))
 assert binding['binding']['bound_entries']==7;report['probes']['p26_sdf_bind']='PASS'
 run([compiler,'p26_tb.sv','--top','tb',*gate,'--sdf-annotate','timing.sdf','--wave-support','--emit-cpp',work/'sdf.cpp','-o',work/'sdf'],work,'sdf-compile')
 wave=work/'sdf-original.vcd';wave.unlink(missing_ok=True)
 assert 'GATE_PROBE: y=1' in run([work/'sdf','--waveform',wave],work,'sdf-run')
 # Original models omit a timescale. Add a default explicitly to exercise
 # nonzero SDF delays instead of rounding them to the default 1s precision.
 run([compiler,'p26_tb.sv','--top','tb',*gate,'--sdf-annotate','timing.sdf','--timescale','1ns/1ps','--wave-support','--emit-cpp',work/'sdf-timed.cpp','-o',work/'sdf-timed'],work,'sdf-timed-compile')
 wave=work/'sdf-timed.vcd';wave.unlink(missing_ok=True)
 assert 'GATE_PROBE: y=1' in run([work/'sdf-timed','--waveform',wave],work,'sdf-timed-run')
 assert timeline(*read(wave))[('tb','y')][2]==[(0,(1,1)),(5000,(0,0)),(12000,(1,0))], 'SDF nonzero delay timeline'
 report['probes']['p26_sdf_annotation']='PASS'
 report.update(status='PASS',original_probes=9)
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS REPORT2:',len(report['designs']),'designs,',report['original_probes'],'probes,',report['captures'],'captures,',report['rollbacks'],'rollbacks')
