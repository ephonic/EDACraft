"""Shared RTL and SDF inputs for actual parallel compiler integration tests."""
import importlib.util
import json
from pathlib import Path
from cases import CASES

ROOT=Path(__file__).resolve().parents[2]

def make(base):
    base.mkdir(parents=True)
    rows=[]
    for name,(source,minimum) in CASES.items():
        work=base/name;work.mkdir();tb=work/'top.v';tb.write_text(source)
        rows.append(dict(name=name,source=tb,flags=[],minimum=minimum))
    for group,names in [('sdf_root_input',['root-reg']),('sdf_runtime',['ff']),('timing_checks',['composed'])]:
        spec=importlib.util.spec_from_file_location('parallel_'+group,ROOT/'tests'/group/'cases.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        inputs=base/group;module.make(inputs)
        golden=json.loads((ROOT/'tests'/group/'expected.json').read_text())
        for name in names:
            work=inputs/name;original=work/'tb.v';tb=work/'parallel-tb.v'
            # An independent source domain makes the four-worker variant
            # execute another kernel alongside the atomic gate scope.
            text=original.read_text();assert text.count('module top;')==1
            tb.write_text(text.replace('module top;',
                'module top;reg autonomous;initial begin autonomous=0;'
                'repeat(80)begin #3 autonomous=~autonomous;end end\n'))
            flags=['--gate-netlist',work/'net.v','--gate-top','dut','--liberty',work/'cells.lib',
                   '--gate-models',work/'cells.v','--sdf-annotate',work/'delay.sdf']
            oracle=golden['cases'][name] if group=='sdf_root_input' else golden[name]
            for backend,options in [
                ('generic',[]),
                ('jobs',['--gate-scalar-timing','--gate-sdf-jobs']),
                ('optimized',['--gate-scalar-timing','--gate-sdf-jobs','--gate-fold-zero-inputs',
                              '--gate-path-dictionary','--time-wheel'])]:
                rows.append(dict(name=group+'-'+name+'-'+backend,source=tb,flags=flags+options,minimum=2,
                                 oracle=oracle,oracle_group=group))
    return rows
