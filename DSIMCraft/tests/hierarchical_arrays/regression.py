"""Keep the reported original AXI4 hierarchical memory observation working."""
from pathlib import Path
import hashlib,json,subprocess,sys
repo=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent/'axi4'
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
report={'status':'RUNNING','sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in fixtures.glob('*.sv')},'variants':{}}
expected=['PASS t1: INCR len3 write+readback','PASS t2: WRAP len3 write+readback','PASS t3: WRAP len7','PASS t4: wstrb halfword','PASS t5: error injections','PASS t6: out-of-order read completion','random bursts done','PASS t8: full memory compare','AXI4_TEST: ALL PASS']
def run(args,label):
 p=subprocess.run(list(map(str,args)),cwd=out,text=True,capture_output=True,timeout=240)
 (out/(label+'.stdout')).write_text(p.stdout);(out/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stdout,p.stderr[-2500:]);return p.stdout
try:
 # The original misleading error is reproducible when only tb.sv is supplied.
 # Missing definitions must identify the module and preserve existing outputs.
 protected=out/'protected.cpp';protected.write_text('keep existing generated code\n')
 p=subprocess.run(list(map(str,[compiler,'--top','tb',fixtures/'tb.sv','--emit-only','--emit-cpp',protected])),cwd=out,text=True,capture_output=True,timeout=240)
 (out/'missing-rtl.stdout').write_text(p.stdout);(out/'missing-rtl.stderr').write_text(p.stderr)
 assert p.returncode!=0 and 'unresolved module axi4_slave (instance dut)' in p.stderr and 'include its RTL source' in p.stderr,p.stderr
 assert 'tb.sv:15:' in p.stderr,p.stderr
 assert 'hierarchical instance is not elaborated: mem' not in p.stderr,p.stderr
 assert protected.read_text()=='keep existing generated code\n'
 report['missing_rtl']='Correct missing-module diagnostic; output preserved'
 for label,files,flags in [('rtl-first',['rtl.sv','tb.sv'],[]),('tb-first',['tb.sv','rtl.sv'],[]),('reference',['rtl.sv','tb.sv'],['--cxx-flag','-DDSIM_REFERENCE_STATIC_NET_DRIVES=1']),('wheel',['rtl.sv','tb.sv'],['--time-wheel']),('parallel',['rtl.sv','tb.sv'],['--threads','2'])]:
  run([compiler,'--top','tb',*[fixtures/name for name in files],*flags,'--emit-cpp',out/(label+'.cpp'),'-o',out/label],label+'-compile')
  text=run([out/label],label+'-run');assert text.splitlines()==expected,(label,text)
  report['variants'][label]='PASS';print('PASS original AXI4 hierarchical mem',label,flush=True)
 report['status']='PASS'
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
