"""Gate-only partition analysis plus unchanged compiled execution behavior."""
import json
from pathlib import Path
import subprocess
import sys

compiler = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
lib = out / 'cells.lib'
lib.write_text('library(l) { cell(BUF) { pin(A) { direction : input; } '
               'pin(Y) { direction : output; function : "A"; } } }\n')
net = out / 'net.v'

def run(command, name, ok=True):
    result = subprocess.run(list(map(str, command)), cwd=out, text=True, capture_output=True, timeout=90)
    (out / (name + '.log')).write_text(result.stdout + result.stderr)
    assert (result.returncode == 0) == ok, (name, result.stdout, result.stderr)
    return result

base = [compiler, '--gate-netlist', net, '--gate-top', 'dut', '--liberty', lib]
for name, inputs, count in [('islands', ['a', 'b', 'c'], 3),
                            ('fanout', ['a', 'a', 'a'], 1),
                            ('constants', ["1'b0"] * 3, 3)]:
    net.write_text('module dut(input a,b,c,output x,y,z);\n' + '\n'.join(
        f'BUF u{i}(.A({a}),.Y({y}));' for i, (a, y) in enumerate(zip(inputs, ['x', 'y', 'z']))) + '\nendmodule\n')
    result = run(base + ['--gate-check', '--gate-partition-report', 4], name)
    analysis = json.loads(result.stdout)['partition_analysis']
    assert analysis['partitions'] == count, (name, analysis)
    assert sum(analysis['instance_counts']) == 3 and analysis['cut_edges'] == 0
    assert len(analysis['instance_partition']) == 3
    assert analysis['execution'] == 'serial' and analysis['scope'] == 'gate-only'

net.write_text('`timescale 1ps/1ps\nmodule dut(input a,output y); wire mid; '
               'BUF u1(.A(a),.Y(mid)); BUF u2(.A(mid),.Y(y)); endmodule\n')
models = out / 'cells.v'
models.write_text('`timescale 1ps/1ps\nmodule BUF(input A,output Y); assign Y=A; '
                  'specify (A=>Y)=(0,0); endspecify endmodule\n')
tb = out / 'tb.v'
tb.write_text('`timescale 1ps/1ps\nmodule top; reg a; wire y; dut d(a,y); '
              'initial begin a=0; #10 $display("TRACE %0t %b",$time,y); a=1; '
              '#10 $display("TRACE %0t %b",$time,y); $finish; end endmodule\n')
sdf = out / 'delay.sdf'
timed = base + ['--gate-models', models, '--sdf-annotate', sdf, tb]
results = {}
for name, off, partitions in [('positive', 3, 2), ('zero-transition', 0, 1)]:
    sdf.write_text('(DELAYFILE (SDFVERSION "3.0") (DIVIDER /) (TIMESCALE 1ps) '
        '(CELL (CELLTYPE "dut") (INSTANCE) (DELAY (ABSOLUTE '
        f'(INTERCONNECT u1/Y u2/A (3:3:3) (3:3:3) ({off}:{off}:{off}))))))\n')
    ir = out / (name + '.json')
    native = out / ('native-' + name)
    run(timed + ['--gate-partition-report', 4, '--emit-ir', ir, '-o', native], name + '-compile')
    analysis = json.loads(ir.read_text())['gate_design']['partition_analysis']
    assert analysis['partitions'] == partitions, analysis
    assert analysis['cut_edges'] == (1 if off else 0)
    assert analysis['lookahead_fs'] == (3000 if off else 0)
    with_report = run([native], name + '-run').stdout
    run(timed + ['-o', native], name + '-serial-compile')
    assert run([native], name + '-serial-run').stdout == with_report
    assert with_report == 'TRACE 10 0\nTRACE 20 1\n'
    results[name] = analysis

for index, value in enumerate(['0', '-1', '65537', 'bad', '1.5', '18446744073709551616']):
    run(base + ['--gate-check', '--gate-partition-report', value], 'invalid-' + str(index), False)
run(base + [tb, '--gate-partition-report', 2], 'missing-ir', False)
(out / 'results.json').write_text(json.dumps(dict(status='PASS', timing=results), indent=2) + '\n')
print('PASS gate partition CLI: independent cones, fanout, replicated constants, positive/zero SDF boundaries and unchanged serial behavior')
