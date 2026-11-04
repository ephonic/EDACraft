"""Default folding, explicit fallback and waveform observability policy."""
from pathlib import Path
import json
import subprocess
import sys
from cases import make

compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
inputs=out/'inputs'
if not inputs.exists():
    make(inputs);make(out/'controls',True)
def run(args,work,label):
    p=subprocess.run(list(map(str,args)),cwd=work,text=True,capture_output=True,timeout=180)
    (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
    assert p.returncode==0,(label,p.stdout,p.stderr)
    return p.stdout
rows={}
for name in ['ic-zero-with-path','ic-zero-with-check','port-multi-zero','ic-positive']:
    source=(out/'controls' if name=='ic-positive' else inputs)/name
    work=out/name;work.mkdir(exist_ok=True)
    tb=(source/'tb.v').read_text().replace(',e(a,b,ze)','')
    tb='\n'.join(line for line in tb.splitlines() if not line.startswith(('initial begin $sdf_annotate','always @')))
    tb=tb.replace('$display("TRACE t=%0t d=%b e=%b",$time,d.u0.A,e.u0.A);','')
    native=work/'tb.v';native.write_text(tb+'\n')
    common=['--gate-netlist',source/'net.v','--gate-top','dut','--liberty',source/'cells.lib',
            '--gate-models',source/'cells.v','--sdf-annotate',source/'delay.sdf',native]
    for variant,flags in [('auto',[]),('off',['--no-gate-fold-zero-inputs']),('force',['--gate-fold-zero-inputs']),
                          ('generic',['--no-gate-scalar-timing']),('wave',['--wave-support'])]:
        run([compiler,*common,*flags,'--emit-cpp',work/(variant+'.cpp'),'--emit-ir',work/(variant+'.json'),
             *(['--emit-only'] if variant=='force' else ['-o',work/variant])],work,variant+'-compile')
    assert (work/'auto.cpp').read_bytes()==(work/'force.cpp').read_bytes()
    auto=json.loads((work/'auto.json').read_text())['gate_design']
    assert auto['scalar_timing'] is True
    assert 'scalar_timing' not in json.loads((work/'generic.json').read_text())['gate_design']
    assert 'scalar_timing' not in json.loads((work/'wave.json').read_text())['gate_design']
    assert auto['zero_input_pins_folded']==(0 if name=='ic-positive' else 1)
    for variant in ['off','wave']:
        assert 'zero_input_pins_folded' not in json.loads((work/(variant+'.json')).read_text())['gate_design']
    outputs=[run([work/variant],work,variant+'-run') for variant in ['auto','off','generic','wave']]
    assert len(set(outputs))==1,(name,outputs)
    if name=='ic-zero-with-path':
        for label,flags,expected in [
            ('last-off',['--gate-scalar-timing','--no-gate-scalar-timing'],False),
            ('last-on',['--no-gate-scalar-timing','--gate-scalar-timing'],True)]:
            run([compiler,*common,*flags,'--emit-only','--emit-ir',work/(label+'.json'),
                 '--emit-cpp',work/(label+'.cpp')],work,label+'-compile')
            assert json.loads((work/(label+'.json')).read_text())['gate_design'].get('scalar_timing',False)==expected
        native.write_text(tb.replace('module top;','module top;initial begin $dumpfile("tasks.vcd");$dumpvars(0,top);end\n')+'\n')
        run([compiler,*common,'--emit-only','--emit-ir',work/'dump.json','--emit-cpp',work/'dump.cpp'],work,'dump-compile')
        assert 'zero_input_pins_folded' not in json.loads((work/'dump.json').read_text())['gate_design']
        assert 'scalar_timing' not in json.loads((work/'dump.json').read_text())['gate_design']
    rows[name]=dict(folded=auto['zero_input_pins_folded'],status='PASS')
    print('PASS default SDF folding',name,flush=True)
(out/'results.json').write_text(json.dumps(dict(status='PASS',cases=rows),indent=2)+'\n')
