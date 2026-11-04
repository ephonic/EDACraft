"""Compile ordinary RTL into automatically assigned independent kernels."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import subprocess
import re
import sys
import tempfile
from fixtures import make
from probes import probe
from fallback import ordinary_cpp

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_waveforms import compare
from run_flow import physical_bits
from reader import read,declarations
p=argparse.ArgumentParser();p.add_argument('compiler',type=Path);p.add_argument('output',type=Path)
p.add_argument('--group',choices=['all','rtl','sdf'],default='all')
a=p.parse_args();compiler=a.compiler.resolve();a.output.mkdir(parents=True,exist_ok=True)
out=Path(tempfile.mkdtemp(prefix='run-',dir=a.output.resolve()))
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=dict(status='RUNNING',directory=str(out),scope=a.group,compiler_sha256=digest(compiler),cases={},captures=0,
            complete_codec_comparisons=0,ordered_signal_comparisons=0,vendor_comparisons=0,
            serial_fallback_identities=0,performance_claim=False)
def save():
    for f in [out/'results.json',a.output/'results.json']:f.write_text(json.dumps(report,indent=2)+'\n')
def run(cmd,w,label,good=True):
    cmd=list(map(str,cmd));(w/(label+'.command.json')).write_text(json.dumps(cmd)+'\n')
    r=subprocess.run(cmd,cwd=w,capture_output=True,text=True,timeout=180)
    for suffix,value in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
        (w/(label+'.'+suffix)).write_text(value)
    assert (r.returncode==0)==good,(label,r.returncode,r.stdout,r.stderr)
    return r
def streams(path):
    meta,events=read(path);values=[[] for _ in meta['signals']]
    for t,k,p in events:
        if k=='value':values[p[0]].append((t,p[1]))
    return {key:(width,ranges,values[id]) for key,(id,width,ranges) in declarations(meta).items()}
try:
    for fixture in make(out/'inputs'):
        if a.group=='rtl' and 'oracle' in fixture:continue
        if a.group=='sdf' and 'oracle' not in fixture:continue
        name=fixture['name'];min_parts=fixture['minimum'];src=fixture['source']
        w=out/name;w.mkdir()
        row=dict(status='RUNNING',source_sha256=digest(src),variants={});report['cases'][name]=row
        reference_stdout=None;reference_bits=None;reference_ordered=None
        for workers in [0,1,4]:
            work=w/str(workers);work.mkdir();exe=work/'simv';cpp=work/'model.cpp';ir=work/'ir.json'
            flags=fixture['flags']+(['--threads',str(workers)] if workers else [])
            run([compiler,src,*flags,'--wave-support','--emit-cpp',cpp,'--emit-ir',ir,'-o',exe],work,'compile')
            data=json.loads(ir.read_text())
            if workers:
                plan=data['parallel'];assert plan['scope']=='whole-program' and plan['cut_edges']==0
                assert plan['partitions']==1 if workers==1 else plan['partitions']>=min_parts
                parallel=plan['execution']=='conservative-kernels'
                assert parallel==(plan['partitions']>1)
                assert ('#define DSIM_PARALLEL_ENABLED 1\n' in cpp.read_text())==parallel
                assert ('engine.run();' in cpp.read_text())==parallel
                setup=[line for line in cpp.read_text().splitlines() if line.startswith('ConservativeSim engine(')]
                assert any(line.endswith('engine.enable_global_finish();') for line in setup)==plan['global_finish_transactions']
                if not parallel:
                    assert ordinary_cpp(cpp.read_text())==(w/'0/model.cpp').read_text()
                    report['serial_fallback_identities']+=1
            else:assert 'parallel' not in data
            result=run([exe,*(['--parallel-stats'] if workers else [])],work,'none')
            if workers:
                line=result.stderr.strip();assert line.startswith('PARALLEL '),line
                stats=json.loads(line[9:]);assert stats['partitions']==data['parallel']['partitions']
                if plan['execution']=='serial-fallback':assert stats['windows']==stats['messages']==0
                if name=='sparse-quiescent':assert stats['windows']==(3 if plan['partitions']>1 else 0)
            else:stats=None
            if reference_stdout is None:reference_stdout=result.stdout
            assert result.stdout==reference_stdout
            if 'oracle' in fixture:
                oracle=fixture['oracle']
                if fixture['oracle_group']=='timing_checks':
                    checks=re.findall(r'^TIMING kind=(\w+) time=(\d+)',result.stdout,re.M)
                    assert [[kind,int(time)] for kind,time in checks]==oracle
                    report['vendor_comparisons']+=len(checks)
                else:
                    assert [line for line in result.stdout.splitlines() if line.startswith('TRACE ')]==oracle['trace']
            if name=='empty':
                failed=run([exe,'--waveform',work/'empty.dwf'],work,'empty-wave',False)
                assert 'selected no signals' in failed.stderr
                row['variants'][str(workers)]=dict(status='PASS',cpp_sha256=digest(cpp),binary_sha256=digest(exe),stats=stats)
                continue
            for mode in ['ordered','settled']:
                reference=None
                for codec,suffix,jobs in [('vcd','vcd',1),('raw','dwf',1),('zstd','dwf',4)]:
                    label=mode+'-'+codec;wave=work/(label+'.'+suffix)
                    args=[exe,'--waveform',wave,'--wave-format',suffix,'--wave-mode',mode,'--wave-block-events','7']
                    if suffix=='dwf':args+=['--wave-codec',codec,'--wave-compression-jobs',str(jobs)]
                    captured=run(args,work,label);assert captured.stdout==reference_stdout
                    if reference:compare(reference,wave);report['complete_codec_comparisons']+=1
                    else:reference=wave
                    bits=physical_bits(wave)
                    if reference_bits is None:reference_bits=bits
                    assert bits==reference_bits,(name,workers,mode,codec,'physical histories')
                    if mode=='ordered' and codec=='vcd':
                        ordered=streams(wave)
                        if reference_ordered is None:reference_ordered=ordered
                        assert ordered==reference_ordered,(name,workers,'ordered individual signal histories')
                        report['ordered_signal_comparisons']+=len(ordered)
                        if fixture.get('oracle_group')=='sdf_root_input':
                            for bit in fixture['oracle']['native_bits']:
                                key=tuple(bit['path'])+(bit['bit'],)
                                assert json.loads(json.dumps(bits[key]))==bit['changes']
                                report['vendor_comparisons']+=1
                        if fixture.get('oracle_group')=='sdf_runtime':
                            for pin,history in fixture['oracle']['pins'].items():
                                # The original 1ps fixture oracle uses ticks;
                                # physical_bits normalizes all wave times to fs.
                                physical=[[time*1000,value] for time,value in history]
                                assert json.loads(json.dumps(bits[('top',pin,None)]))==physical
                                report['vendor_comparisons']+=1
                    report['captures']+=1
            row['variants'][str(workers)]=dict(status='PASS',cpp_sha256=digest(cpp),binary_sha256=digest(exe),stats=stats)
        row['status']='PASS';save();print('PASS automatic RTL',name,flush=True)
    report['probes']=probe(compiler,out/'probes',run)
    report['status']='PASS'
except BaseException as e:
    report.update(status='FAIL',error=repr(e));raise
finally:save()
print('PASS compiled whole-program automatic independent-domain execution')
