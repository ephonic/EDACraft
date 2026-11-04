"""Actual COND/CONDELSE compilation, full codecs, rollback and strict rejection."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
from cases import make
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from compare_waveforms import compare
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cases=make(out/'inputs')
config={line.split('=',1)[0].split(':',1)[0]:line.split('=',1)[1] for line in (compiler.parent/'CMakeCache.txt').read_text().splitlines() if '=' in line and not line.startswith('//')}
report=dict(status='RUNNING',cases={},native_captures=0,checkpoint_captures=0)
def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
def run(command,work,label,success=True):
    (work/(label+'.command.json')).write_text(json.dumps(list(map(str,command)),indent=2)+'\n')
    result=subprocess.run(list(map(str,command)),cwd=work,text=True,capture_output=True,timeout=240)
    (work/(label+'.stdout')).write_text(result.stdout);(work/(label+'.stderr')).write_text(result.stderr)
    assert (result.returncode==0)==success,(label,result.returncode,result.stdout,result.stderr)
    return result.stdout,result.stderr
def arguments(work):
    return ['--gate-netlist',work/'net.v','--gate-top','dut','--liberty',work/'cells.lib',
            '--gate-models',work/'cells.v','--sdf-annotate',work/'delay.sdf',work/'tb.v']
try:
    save()
    for name,case in cases.items():
        source=out/'inputs'/name;work=out/name;work.mkdir(exist_ok=True);reference={}
        for variant in ['generic','scalar','wheel','scalar-wheel']:
            flags=(['--gate-scalar-timing'] if 'scalar' in variant else [])+(['--time-wheel'] if 'wheel' in variant else [])
            run([compiler,*arguments(source),*flags,'--wave-support','--emit-cpp',work/(variant+'.cpp'),
                 '--emit-ir',work/(variant+'.json'),'-o',work/variant],work,variant+'-compile')
            assert '#define DSIM_CONDITIONAL_PATH_ENABLED 1' in (work/(variant+'.cpp')).read_text()
            ir=json.loads((work/(variant+'.json')).read_text());assert ir['gate_design']['conditional_module_paths']
            baseline=run([work/variant],work,variant+'-none');assert baseline[0].splitlines()==case['expected'],(name,variant,baseline)
            assert not baseline[1],(name,variant,baseline[1])
            for mode in ['ordered','settled']:
                for codec,ext in [('vcd','vcd'),('raw','dwf'),('zstd','dwf')]:
                    label=variant+'-'+mode+'-'+codec;wave=work/(label+'.'+ext);wave.unlink(missing_ok=True)
                    command=[work/variant,'--waveform',wave,'--wave-format',ext,'--wave-mode',mode,'--wave-block-events','7']
                    if ext=='dwf':command+=['--wave-codec',codec]
                    assert run(command,work,label)==baseline
                    if mode not in reference:reference[mode]=wave
                    compare(reference[mode],wave);report['native_captures']+=1
            print('PASS conditional paths',name,variant,flush=True)
        report['cases'][name]=dict(status='PASS',expected=case['expected'],variants=4);save()
    work=out/'truth'
    control='''
s.run_until(111);
auto accepted=s.predict_until(125,[](Sim& probe){
 for(size_t i=0;i<probe.signals.size();++i){const auto& sig=probe.signals[i];if(!sig.net)probe.set(int(i),V::x(sig.value.w));}
},[](const Sim&){return false;},[](Sim&){});
if(accepted||s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing conditional-path rollback");
s.run();
'''
    for queue in ['scalar','scalar-wheel']:
        code=(work/(queue+'.cpp')).read_text();assert code.count('\ns.run();\n')==1
        for variant,body in [('boundary','\ns.run_until(111);s.run_until(125);s.run();\n'),('replay',control)]:
            prefix=queue+'-'+variant;(work/(prefix+'.cpp')).write_text(code.replace('\ns.run();\n',body))
            run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/(prefix+'.cpp'),config['DSIM_ZSTD_LIBRARY'],'-o',work/prefix],work,prefix+'-compile')
            for mode in ['ordered','settled']:
                for codec in ['raw','zstd']:
                    label=prefix+'-'+mode+'-'+codec;dest=work/(label+'.dwf');dest.unlink(missing_ok=True)
                    stdout,stderr=run([work/prefix,'--waveform',dest,'--wave-codec',codec,'--wave-mode',mode,'--wave-block-events','7'],work,label)
                    assert stdout.splitlines()==cases['truth']['expected'] and not stderr
                    report['checkpoint_captures']+=1
        for mode in ['ordered','settled']:
            for codec in ['raw','zstd']:compare(work/(queue+'-boundary-'+mode+'-'+codec+'.dwf'),work/(queue+'-replay-'+mode+'-'+codec+'.dwf'))
    strict=out/'strict';strict.mkdir(exist_ok=True)
    original=out/'inputs/truth';source=(original/'cells.v').read_text();sdf=(original/'delay.sdf').read_text()
    for n in ['net.v','cells.lib','tb.v']:shutil.copyfile(original/n,strict/n)
    rejections={
        'ifnone-unconditional':(source.replace('endspecify','(A=>Z)=0;endspecify'),sdf,'ifnone and unconditional'),
        'ifnone-edge':(source.replace('ifnone(A=>Z)','ifnone(posedge A=>(Z:A))'),sdf,'ifnone requires a simple path'),
        'arithmetic':(source.replace('if(E)','if(E+1)'),sdf.replace('COND E ','COND E+1 '),'unsupported timing condition'),
        'alias-cycle':(source.replace('assign Z=A;','wire EN;assign EN=EN;assign Z=A;').replace('if(E)','if(EN)'),sdf.replace('COND E ','COND EN '),'cyclic/deep timing condition alias'),
    }
    for name,(model,annotation,message) in rejections.items():
        (strict/'cells.v').write_text(model);(strict/'delay.sdf').write_text(annotation)
        cpp=strict/'protected.cpp';ir=strict/'protected.json';cpp.write_text('keep-cpp');ir.write_text('keep-ir')
        _,error=run([compiler,*arguments(strict),'--emit-only','--emit-cpp',cpp,'--emit-ir',ir],strict,name,False)
        assert message in error,(name,error)
        assert cpp.read_text()=='keep-cpp' and ir.read_text()=='keep-ir'
    report.update(status='PASS',strict_rejections=list(rejections),generated_replay=True)
finally:save()
