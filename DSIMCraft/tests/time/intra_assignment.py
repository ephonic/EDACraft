"""Execute sampled blocking delays and restore pending samples/PC/waves."""
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read

compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
def run(args,log,success=True):
    p=subprocess.run(list(map(str,args)),cwd=out,text=True,capture_output=True,timeout=180)
    (out/log).write_text(p.stdout+p.stderr)
    assert (p.returncode==0)==success,(args,p.stdout,p.stderr)
    return p.stdout+p.stderr
run([compiler,ROOT/'tests/time/intra_assignment.v','--wave-support','--emit-cpp',out/'model.cpp','-o',out/'baseline'],'compile.log')
code=(out/'model.cpp').read_text();assert 'delay_value' in code
cache=(compiler.parent/'CMakeCache.txt').read_text().splitlines()
config={line.split('=',1)[0].split(':',1)[0]:line.split('=',1)[1] for line in cache if '=' in line and not line.startswith('//')}
control='''
s.run_until(1000);
if(s.finished)throw std::runtime_error("unexpected early finish");
bool accepted=s.predict_until(12000,[](Sim& probe) {
 for(size_t id=0;id<probe.signals.size();++id) {
  const auto& sig=probe.signals[id];if(!sig.net)probe.set(int(id),V::ones(sig.value.w));
 }
},[](const Sim&){return false;},[](Sim&){});
if(accepted||s.prediction_stats.rollbacks!=1)throw std::runtime_error("pending sampled delay rollback failed");
s.run();
'''
assert code.count('\ns.run();\n')==1
(out/'replay.cpp').write_text(code.replace('\ns.run();\n',control))
run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],out/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',out/'replay'],'replay-compile.log')
expected=['TRACE coarse t=0 q=11','TRACE sampled t=5000 q=12 source=34','TRACE delta t=5000 q=34',
          'TRACE parts t=9000 hi=3 lo=4','TRACE wide t=12000 q='+'2'*64,
          'TRACE delayed t=14000 q=56','TRACE unknown t=15000 q=xz',
          'TRACE repeat t=16000 q=01','TRACE repeat t=17000 q=02','TRACE repeat t=18000 q=03']
for mode in ['ordered','settled']:
    outputs=[];waves=[]
    for variant in ['baseline','replay']:
        for fmt in ['vcd','dwf']:
            dest=out/(variant+'-'+mode+'.'+fmt);dest.unlink(missing_ok=True)
            text=run([out/variant,'--waveform',dest,'--wave-format',fmt,'--wave-mode',mode,'--wave-block-events','7'],variant+'-'+mode+'-'+fmt+'.log')
            assert text.splitlines()==expected,(mode,variant,text,expected)
            outputs.append(text);waves.append(read(dest))
    assert len(set(outputs))==1
    assert all(w==waves[0] for w in waves)
# Intra-assignment event controls are supported: sample the RHS before waiting.
src=out/'event.v';src.write_text('''module top;
reg clk=0;reg[7:0] source=8'h11,q=0;
initial begin q = @(posedge clk) source;if(q!=8'h11)$fatal(1,"event RHS was not sampled");$display("TRACE event q=%h",q);end
initial begin #1;source=8'h22;#1;clk=1;#1;$finish;end
endmodule
''')
run([compiler,src,'--emit-cpp',out/'event.cpp','-o',out/'event'],'event-compile.log')
assert run([out/'event'],'event-run.log').splitlines()==['TRACE event q=11']
(out/'results.json').write_text(json.dumps(dict(status='PASS',expected_trace=expected,rollback=True,full_native_waves=True),indent=2)+'\n')
print('PASS sampled RTL delays: #0, module precision, concatenations, wide/four-state values, repeat and actual rollback/waves')
