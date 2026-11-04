"""Compile SDF jobs through the actual CLI and compare every ordered event."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_waveforms import compare
compiler=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
config={line.split('=',1)[0].split(':',1)[0]:line.split('=',1)[1]
        for line in (compiler.parent/'CMakeCache.txt').read_text().splitlines()
        if '=' in line and not line.startswith('//')}
def fixtures(name,source,destination):
    spec=importlib.util.spec_from_file_location(name,ROOT/source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.make(destination)
fixtures('ic_cases','tests/sdf_interconnect/cases.py',out/'inputs/ic')
fixtures('check_cases','tests/timing_checks/cases.py',out/'inputs/checks')
conditional=fixtures('condition_cases','tests/sdf_conditional/cases.py',out/'inputs/conditional')
cases={name:out/'inputs/ic'/name for name in ['fanout','pulses','multi-driver']}
cases.update({'checks-'+name:out/'inputs/checks'/name for name in ['composed','delta']})
cases.update({'condition-'+name:out/'inputs/conditional'/name for name in ['truth','output-state','unconditional-tie']})
report=dict(status='RUNNING',cases={},native_captures=0,checkpoint_captures=0)
def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
def run(command,work,label,success=True):
    command=list(map(str,command))
    (work/(label+'.command.json')).write_text(json.dumps(command,indent=2)+'\n')
    result=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=240)
    (work/(label+'.stdout')).write_text(result.stdout);(work/(label+'.stderr')).write_text(result.stderr)
    assert (result.returncode==0)==success,(label,result.returncode,result.stdout,result.stderr)
    return result.stdout,result.stderr
def arguments(work):
    return ['--gate-netlist',work/'net.v','--gate-top','dut','--liberty',work/'cells.lib',
            '--gate-models',work/'cells.v','--sdf-annotate',work/'delay.sdf',work/'native-tb.v',
            '--gate-scalar-timing']
try:
    save()
    for name,source in cases.items():
        tb=(source/'tb.v').read_text()
        if name in ['fanout','pulses','multi-driver']:
            tb='\n'.join('always @(x or y) $display("TRACE t=%0t x=%b y=%b",$time,x,y);'
                         if line.startswith('always @') else line for line in tb.splitlines())+'\n'
        (source/'native-tb.v').write_text(tb)
        work=out/name;work.mkdir(exist_ok=True);baseline=None
        for backend in ['scalar','scalar-wheel','jobs','jobs-wheel']:
            flags=(['--gate-sdf-jobs'] if backend.startswith('jobs') else [])
            if 'wheel' in backend:flags+=['--time-wheel']
            run([compiler,*arguments(source),*flags,'--wave-support',
                 '--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),
                 '-o',work/backend],work,backend+'-compile')
            cpp=(work/(backend+'.cpp')).read_text();ir=json.loads((work/(backend+'.json')).read_text())
            jobs=backend.startswith('jobs')
            assert ('#define DSIM_SDF_JOBS_ENABLED 1' in cpp)==jobs
            assert ir['gate_design'].get('sdf_jobs',False)==jobs
            assert ('s.initialize_sdf_jobs_and_processes(' in cpp)==jobs
            if jobs:
                assert 's.arm_fixed_wait(input.site);' not in cpp and 's.arm_fixed_wait(output.site);' not in cpp
                assert 's.compiled_process(path_handler,uint32_t(i))' not in cpp
                assert 's.compiled_process(input_handler,uint32_t(i))' not in cpp
            result=run([work/backend],work,backend+'-none')
            if baseline is None:baseline=result
            assert result==baseline,(name,backend)
            if name.startswith('condition-'):
                assert result[0].splitlines()==conditional[name.removeprefix('condition-')]['expected']
                assert not result[1]
            for mode in ['ordered','settled']:
                for codec,extension in [('vcd','vcd'),('raw','dwf'),('zstd','dwf')]:
                    label=backend+'-'+mode+'-'+codec;wave=work/(label+'.'+extension)
                    wave.unlink(missing_ok=True)
                    command=[work/backend,'--waveform',wave,'--wave-format',extension,
                             '--wave-mode',mode,'--wave-block-events','7']
                    if codec!='vcd':command+=['--wave-codec',codec]
                    assert run(command,work,label)==baseline
                    compare(work/('scalar-'+mode+'-vcd.vcd'),wave)
                    report['native_captures']+=1
            # Budget failures must occur at the same FIFO/RTL instruction
            # boundary, including partially completed initialization.
            for budget in [1,5,10,25,50]:
                run([work/backend,'--max-events',str(budget)],work,backend+'-budget-'+str(budget),False)
                for stream in ['stdout','stderr']:
                    assert (work/(backend+'-budget-'+str(budget)+'.'+stream)).read_bytes()==(work/('scalar-budget-'+str(budget)+'.'+stream)).read_bytes()
        report['cases'][name]=dict(status='PASS',trace=baseline[0].splitlines(),backends=4)
        save();print('PASS actual SDF jobs/scalar, full streams and budget boundaries',name,flush=True)
    for name in ['checks-composed','condition-truth']:
        work=out/name;expected=(work/'jobs-none.stdout').read_text();errors=(work/'jobs-none.stderr').read_text()
        for backend in ['jobs','jobs-wheel']:
            cpp=(work/(backend+'.cpp')).read_text();assert cpp.count('\ns.run();\n')==1
            control='''
s.run_until(101);
auto accepted=s.predict_until(125,[](Sim& probe){
 for(size_t i=0;i<probe.signals.size();++i){const auto& signal=probe.signals[i];if(!signal.net)probe.set(int(i),V::x(signal.value.w));}
},[](const Sim&){return false;},[](Sim&){});
if(accepted||s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing SDF jobs rollback");
s.run();
'''
            for variant,body in [('boundary','\ns.run_until(101);s.run_until(125);s.run();\n'),('replay',control)]:
                label=backend+'-'+variant;(work/(label+'.cpp')).write_text(cpp.replace('\ns.run();\n',body))
                run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/(label+'.cpp'),
                     config['DSIM_ZSTD_LIBRARY'],'-o',work/label],work,label+'-compile')
                for mode in ['ordered','settled']:
                    wave=work/(label+'-'+mode+'.dwf');wave.unlink(missing_ok=True)
                    assert run([work/label,'--waveform',wave,'--wave-mode',mode,'--wave-codec','zstd',
                                '--wave-block-events','7'],work,label+'-'+mode)==(expected,errors)
                    compare(wave,work/('jobs-boundary-'+mode+'.dwf'))
                    report['checkpoint_captures']+=1
    # This backend is explicit and cannot silently apply to parser/check-only
    # commands or overwrite outputs when its required scalar option is absent.
    strict=out/'strict';strict.mkdir(exist_ok=True)
    protected=strict/'protected.cpp';ir=strict/'protected.json'
    protected.write_text('keep-cpp');ir.write_text('keep-ir')
    source=cases['condition-truth'];args=arguments(source);args.remove('--gate-scalar-timing')
    _,error=run([compiler,*args,'--gate-sdf-jobs','--emit-only','--emit-cpp',protected,'--emit-ir',ir],
                strict,'missing-scalar',False)
    assert '--gate-sdf-jobs requires --gate-scalar-timing' in error
    assert protected.read_text()=='keep-cpp' and ir.read_text()=='keep-ir'
    report.update(status='PASS',generated_replay=True,budget_boundaries_each=5)
finally:save()
