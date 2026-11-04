"""Single receiver thread owns DWF encoding, compression and all file I/O."""
from pathlib import Path
import importlib.util,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'tests/waveform'))
from compare_waveforms import compare
from reader import read,dwf
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]) if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={s.split('=',1)[0].split(':',1)[0]:s.split('=',1)[1] for s in cache.read_text().splitlines() if '=' in s and not s.startswith('//')}
report=dict(status='RUNNING',captures=0,byte_identical_pairs=0,invalid_options=0,cases={},rollbacks=0,commits=0)
def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
def run(args,work,label,ok=True):
 p=subprocess.run(list(map(str,args)),cwd=work,text=True,capture_output=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode>=0,(label,'crash',p.returncode,p.stderr)
 assert (not p.returncode)==ok,(label,p.stdout,p.stderr)
 return p.stdout,p.stderr
def native(source,exe,label):
 flags=['-fp-model=strict'] if Path(config['DSIM_MODEL_CXX']).name in ('icpx','icpc') else []
 return run([config['DSIM_MODEL_CXX'],'-std=c++17','-O2','-pthread',*flags,'-I'+str(ROOT/'include'),'-I'+config['DSIM_ZSTD_INCLUDE'],source,config['DSIM_ZSTD_LIBRARY'],'-o',exe],out,label)
try:
 save();native(ROOT/'tests/waveform_pipeline/kernel.cpp',out/'kernel','kernel-compile')
 # Kernel owns exclusive files; use a fresh directory under each regression.
 kernel_dir=out/'kernel-files';kernel_dir.mkdir(exist_ok=False)
 run([out/'kernel',kernel_dir],out,'kernel-run');report['cases']['thread_ownership_errors_budget_snapshot']='PASS'
 # Check the receiver's decoded values against independent Python integers,
 # rather than relying only on two encoders producing identical bytes.
 expected=[(0,'time',None),(0,'control',['$dumpvars'])]
 for t in range(120):
  if t and t%3==0:expected.append((t//3,'time',None))
  for ident,width in enumerate([1,65,1024,4096]):
   aval=sum((0x123456789abcdef0 ^ (t*127+j)) << (j*64) for j in range((width+63)//64)) & ((1<<width)-1)
   bval=(1<<width)-1 if t%7==0 else 0
   expected.append((t//3,'value',(ident,(aval,bval))))
 expected.append((39,'control',['$end']))
 for name in ['sync','async']:
  _,events=read(kernel_dir/(name+'.dwf'));assert events==expected,(name,'wide four-state snapshot oracle')
 report['kernel_value_oracle']=480;report['cases']['close_error_and_idempotence']='PASS'
 spec=importlib.util.spec_from_file_location('sdf_cases',ROOT/'tests/sdf_zero_input/cases.py');cases=importlib.util.module_from_spec(spec);spec.loader.exec_module(cases)
 cases.make(out/'sdf-inputs');src=out/'sdf-inputs/ic-zero-with-path'
 tb=(src/'tb.v').read_text().replace(',e(a,b,ze)','')
 tb='\n'.join(s for s in tb.splitlines() if not s.startswith(('initial begin $sdf_annotate','always @')))
 tb=tb.replace('$display("TRACE t=%0t d=%b e=%b",$time,d.u0.A,e.u0.A);','');(src/'native.v').write_text(tb+'\n')
 rtl=out/'top.sv';rtl.write_text('''`timescale 1ps/1ps
module top;reg [256:0] a;wire [256:0] y;assign y=~a;
initial begin a=0;#1;a=257'h1;#0;a=257'h7;#3;a=257'bx;#1;a=257'bz;#3;$finish;end endmodule
''')
 dump=out/'dump.sv';dump.write_text('''`timescale 1ps/1ps
module top;logic [7:0] q=0;
initial begin $dumpvars;#1;q=3;$dumpall;#1;$dumpoff;q=5;#1;$dumpon;#1;q=7;$finish;end endmodule
''')
 fixtures=[('rtl',[rtl],(1,4,6)),('sdf',['--gate-netlist',src/'net.v','--gate-top','dut','--liberty',src/'cells.lib','--gate-models',src/'cells.v','--sdf-annotate',src/'delay.sdf','--gate-scalar-timing','--gate-sdf-jobs','--gate-fold-zero-inputs',src/'native.v'],(11,35,75)),('parallel',[ROOT/'tests/uvm_containers/parallel.sv','--threads','2'],None),('dump',[dump],None)]
 for name,args,horizons in fixtures:
  work=out/name;work.mkdir(exist_ok=True);exe=work/'sim';cpp=work/'model.cpp'
  run([compiler,*args,'--wave-support','--emit-cpp',cpp,'-o',exe],work,'compile')
  if name=='parallel':
   _,stderr=run([exe,'--parallel-stats'],work,'stats');assert '"partitions":2' in stderr
  executables=[exe]
  if horizons:
   first,wrong,accepted=horizons;code=cpp.read_text();assert code.count('\ns.run();\n')==1
   replay=code.replace('\ns.run();\n',f'''
s.run_until({first});
if(s.predict_until({wrong},[](Sim&){{}},[](const Sim&){{return false;}},[](Sim&){{}}))throw std::runtime_error("prediction committed");
if(!s.predict_until({accepted},[](Sim&){{}},[](const Sim&){{return true;}},[](Sim&){{}}))throw std::runtime_error("prediction failed");
if(s.prediction_stats.rollbacks!=1||s.prediction_stats.commits!=1)throw std::runtime_error("transaction stats");
s.run();
''')
   (work/'replay.cpp').write_text(replay);native(work/'replay.cpp',work/'replay',name+'-replay-compile');executables.append(work/'replay')
  for program in executables:
   for mode in ['ordered','settled']:
    for block in [1,17,16384]:
     stem=program.name+'-'+mode+'-'+str(block);sync=work/(stem+'-sync.dwf');async_=work/(stem+'-async.dwf')
     for path,extra in [(sync,[]),(async_,['--wave-async','--wave-buffer-bytes','4096'])]:
      path.unlink(missing_ok=True)
      stdout,stderr=run([program,'--waveform',path,'--wave-mode',mode,'--wave-block-events',block,'--wave-stats',*extra],work,path.stem)
      report['captures']+=1
      if not extra:baseline=stdout
      else:
       assert stdout==baseline
       line=next(s for s in stderr.splitlines() if s.startswith('WAVE_ASYNC '));stats=json.loads(line.split(' ',1)[1]);assert stats['writer_threads']==1 and stats['peak_pending_bytes']<=4096
     compare(sync,async_);assert sync.read_bytes()==async_.read_bytes();report['byte_identical_pairs']+=1
  if horizons:report['rollbacks']+=1;report['commits']+=1
  report['cases'][name]='PASS';save()
 # No invalid combination may create a new output file.
 for flags in [['--wave-async','--wave-format','vcd'],['--wave-async','--wave-codec','raw'],['--wave-async','--wave-compression-jobs','2'],['--wave-buffer-bytes','4096'],['--wave-async','--wave-buffer-bytes','0'],['--wave-async','--wave-buffer-bytes','67108865'],['--wave-async','--wave-buffer-bytes','x']]:
  i=report['invalid_options'];path=out/('invalid-'+str(i)+'.dwf');path.unlink(missing_ok=True)
  run([out/'rtl/sim','--waveform',path,*flags],out,'invalid-'+str(i),False);assert not path.exists();report['invalid_options']+=1
 # A completed async file remains usable for indexed windows and interrupted recovery.
 source=out/'rtl/sim-ordered-1-async.dwf'
 with source.open('rb') as f:
  decoder=dwf.Reader(f);events=read(source)[1];state,window=decoder.window(1,4);assert window==[e for e in events if 1<=e[0]<=4]
  index=decoder.index
 damaged=out/'truncated.dwf';damaged.write_bytes(source.read_bytes()[:index[-1][3]-1])
 recovered=out/'recovered.dwf';recovered.unlink(missing_ok=True);proof=dwf.recover(damaged,recovered);assert proof['blocks_recovered']==len(index)-1
 read(recovered);report['cases']['indexed_window_and_recovery']='PASS'
 # Unified flow applies async options only to compressed capture.
 manifest=out/'flow.json';manifest.write_text(json.dumps(dict(cases=[dict(name='async',sources=[str(ROOT/'tests/uvm_containers/queues.sv')],wave_async=True,wave_buffer_bytes=4096)])))
 # Validate configuration via run_flow's real command path.
 run([sys.executable,ROOT/'scripts/run_flow.py',manifest,'--dsim',compiler,'--output',out/'flow'],out,'flow')
 report['cases']['flow_manifest']='PASS';report['status']='PASS'
finally:save()
print('PASS waveform pipeline:',report['captures'],'captures,',report['byte_identical_pairs'],'byte-identical pairs,',report['invalid_options'],'reject cases')
