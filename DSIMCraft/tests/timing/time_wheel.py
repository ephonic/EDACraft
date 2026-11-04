"""Exercise the queue through real RTL/SDF compilation and full waveform streams."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests/time')]
from compare_waveforms import compare
from continuous_delay_cases import CASES as CONT,IEEE_CASES
from delayed_nba_cases import CASES as NBA

compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
config={line.split('=',1)[0].split(':',1)[0]:line.split('=',1)[1]
        for line in (compiler.parent/'CMakeCache.txt').read_text().splitlines() if '=' in line and not line.startswith('//')}
def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
load_module('interconnect_cases',ROOT/'tests/sdf_interconnect/cases.py').make(out/'inputs')
load_module('check_cases',ROOT/'tests/timing_checks/cases.py').make(out/'checks')
cases={}
plain='''`timescale 1ps/1ps
module top;reg [7:0] q=0;reg [31:0] i;
initial begin
 for(i=0;i<5;i=i+1)begin #1;q=q+1;#0;$display("TRACE near q=%h",q);end
 #256;q=8'hxz;#0;$display("TRACE far q=%h",q);
 #1000000;q=8'h5a;#0;$display("TRACE jump q=%h",q);$finish;
end endmodule
'''
cases['rtl']=(plain,[],['TRACE near q=0'+str(i) for i in range(1,6)]+['TRACE far q=xz','TRACE jump q=5a'])
for name in ['parts','matrix']:
    source,expected=CONT[name];cases['continuous-'+name]=(source,[],expected)
cases['ieee-vector']=(IEEE_CASES['vector'][0],['--continuous-delay-mode','ieee'],IEEE_CASES['vector'][1])
cases['nba']=(NBA['parts'][0],[],NBA['parts'][1])
report=dict(status='RUNNING',cases={},native_captures=0,generated_replay=False)
def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
def run(command,work,label,success=True):
    (work/(label+'.command.json')).write_text(json.dumps(list(map(str,command)),indent=2)+'\n')
    result=subprocess.run(list(map(str,command)),cwd=work,text=True,capture_output=True,timeout=240)
    (work/(label+'.stdout')).write_text(result.stdout);(work/(label+'.stderr')).write_text(result.stderr)
    assert (result.returncode==0)==success,(str(work),label,result.returncode,result.stderr)
    return result.stdout
def exercise(name,work,arguments,expected=None):
    streams={};errors={};waves={}
    for backend in ['heap','wheel']:
        command=[compiler,*arguments,'--wave-support','--emit-ir',work/(backend+'.json'),
                 '--emit-cpp',work/(backend+'.cpp'),'-o',work/backend]
        if backend=='wheel':command+=['--time-wheel']
        run(command,work,backend+'-compile')
        code=(work/(backend+'.cpp')).read_text()
        assert ('#define DSIM_TIME_WHEEL_ENABLED 1' in code)==(backend=='wheel')
        ir=json.loads((work/(backend+'.json')).read_text())
        assert ir.get('time_queue')==('near-far' if backend=='wheel' else None)
        streams[backend]=run([work/backend],work,backend+'-none')
        errors[backend]=(work/(backend+'-none.stderr')).read_text()
        if expected is not None:assert streams[backend].splitlines()==expected,(name,backend)
        waves[backend]={}
        for mode in ['ordered','settled']:
            for codec,fmt in [('vcd','vcd'),('raw','dwf'),('zstd','dwf')]:
                label=backend+'-'+mode+'-'+codec;dest=work/(label+'.'+fmt);dest.unlink(missing_ok=True)
                command=[work/backend,'--waveform',dest,'--wave-format',fmt,'--wave-mode',mode,'--wave-block-events','7']
                if fmt=='dwf':command+=['--wave-codec',codec]
                assert run(command,work,label)==streams[backend]
                assert (work/(label+'.stderr')).read_text()==errors[backend],(name,label,'stderr')
                waves[backend][mode,codec]=dest;report['native_captures']+=1
            for codec in ['raw','zstd']:compare(waves[backend][mode,'vcd'],waves[backend][mode,codec])
    assert streams['heap']==streams['wheel'],name
    assert errors['heap']==errors['wheel'],(name,'stderr')
    for key,path in waves['heap'].items():compare(path,waves['wheel'][key])
    report['cases'][name]=dict(status='PASS',trace=streams['heap'].splitlines(),full_ordered_settled_streams_equal=True)
    save();print('PASS actual heap/wheel compilation and complete streams',name,flush=True)
try:
    save()
    for name,(source,flags,expected) in cases.items():
        work=out/name;work.mkdir(exist_ok=True);(work/'top.v').write_text(source)
        exercise(name,work,[work/'top.v',*flags],expected)
    for name,work in [('fanout',out/'inputs/fanout'),('checks',out/'checks/composed')]:
        tb=(work/'tb.v').read_text()
        if name=='fanout':tb='\n'.join('always @(x or y) $display("TRACE t=%0t x=%b y=%b",$time,x,y);' if s.startswith('always @') else s for s in tb.splitlines())+'\n'
        (work/'native-tb.v').write_text(tb)
        for scalar in [False,True]:
            variant=name+('-scalar' if scalar else '-generic')
            dest=out/variant;dest.mkdir(exist_ok=True)
            args=['--gate-netlist',work/'net.v','--gate-top','dut','--liberty',work/'cells.lib',
                  '--gate-models',work/'cells.v','--sdf-annotate',work/'delay.sdf',work/'native-tb.v']
            if scalar:args+=['--gate-scalar-timing']
            exercise(variant,dest,args)
    work=out/'checks-scalar'
    code=(work/'wheel.cpp').read_text();assert code.count('\ns.run();\n')==1
    control='''
s.run_until(101);
auto accepted=s.predict_until(125,[](Sim& probe){
 for(size_t id=0;id<probe.signals.size();++id){const auto& sig=probe.signals[id];if(!sig.net)probe.set(int(id),V::x(sig.value.w));}
},[](const Sim&){return false;},[](Sim&){});
if(accepted||s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing queue rollback");
s.run();
'''
    (work/'replay.cpp').write_text(code.replace('\ns.run();\n',control))
    (work/'boundary.cpp').write_text(code.replace('\ns.run();\n','\ns.run_until(101);s.run_until(125);s.run();\n'))
    for variant in ['replay','boundary']:
        run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/(variant+'.cpp'),config['DSIM_ZSTD_LIBRARY'],'-o',work/variant],work,variant+'-compile')
        for mode in ['ordered','settled']:
            dest=work/(variant+'-'+mode+'.dwf');dest.unlink(missing_ok=True)
            stdout=run([work/variant,'--waveform',dest,'--wave-mode',mode,'--wave-codec','zstd','--wave-block-events','7'],work,variant+'-'+mode)
            assert stdout==(work/'wheel-none.stdout').read_text()
            assert (work/(variant+'-'+mode+'.stderr')).read_text()==(work/'wheel-none.stderr').read_text()
    for mode in ['ordered','settled']:compare(work/('replay-'+mode+'.dwf'),work/('boundary-'+mode+'.dwf'))
    for args in [[],['-E'],['--gate-check'],['--sdf-check','missing.sdf'],['--timing-model-check']]:
        result=subprocess.run([str(compiler),'--time-wheel',*args],capture_output=True,text=True)
        assert result.returncode and ('--time-wheel' in result.stderr or 'no Verilog input' in result.stderr)
    report.update(status='PASS',generated_replay=True,checkpoint_captures=4)
finally:save()
