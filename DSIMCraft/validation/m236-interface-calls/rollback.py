"""Compare identical bounded windows before and after process lifetime waits are registered."""
from pathlib import Path
import json,subprocess,sys
root,normal,cache,out=map(lambda p:Path(p).resolve(),sys.argv[1:5]);out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(root/'tests/waveform'));from reader import read
config={s.split('=',1)[0].split(':',1)[0]:s.split('=',1)[1] for s in cache.read_text().splitlines() if '=' in s and not s.startswith('//')}
assert json.loads((normal/'results.json').read_text())['status']=='PASS','wait for the complete native regression before checkpoint comparisons'
expected=json.loads((root/'tests/virtual_interface_calls/expected.json').read_text());report=dict(status='RUNNING',models={},failed_predictions=0)
try:
 cases=[('basic','before_allocation'),('basic','after_binding'),('reentry','after_binding'),('arguments','after_binding')]
 for name,phase in cases:
  w=out/(name+'-'+phase);w.mkdir(exist_ok=True);code=(normal/name/'shared.cpp').read_text();assert code.count('\ns.run();\n')==1
  prelude='s.run_until(0);\n' if phase=='after_binding' else ''
  reference=prelude+'s.run_until(10000);\ns.run();\n'
  speculative=prelude+'if(s.predict_until(10000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");\nif(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");\ns.run();\n'
  for mode,replacement in [('reference',reference),('prediction',speculative)]:
   cpp=w/(mode+'.cpp');cpp.write_text(code.replace('\ns.run();\n','\n'+replacement))
   for label,args in [('compile',[config['DSIM_MODEL_CXX'],'-std=c++17','-O2','-pthread','-I'+config['DSIM_ZSTD_INCLUDE'],cpp,config['DSIM_ZSTD_LIBRARY'],'-o',w/mode]),('run',[w/mode,'--waveform',w/(mode+'.vcd'),'--wave-format','vcd','--wave-mode','ordered'])]:
    p=subprocess.run(list(map(str,args)),cwd=w,capture_output=True,text=True,timeout=600)
    (w/(mode+'-'+label+'.stdout')).write_text(p.stdout);(w/(mode+'-'+label+'.stderr')).write_text(p.stderr);assert not p.returncode,(name,phase,mode,label,p.stderr[-3000:])
   assert p.stdout.splitlines()==expected[name],(name,phase,mode,p.stdout)
  assert read(w/'reference.vcd')==read(w/'prediction.vcd'),(name,phase,'full bounded waveform')
  report['models'][name+'-'+phase]=dict(status='PASS',complete_waveform_identity=True,checkpoint_phase=phase)
  report['failed_predictions']+=1;print('PASS rollback',name,phase,flush=True)
 report['status']='PASS'
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
