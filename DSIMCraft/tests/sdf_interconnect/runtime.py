"""End-to-end compiled wire delays, compressed waves and existing VCS oracles."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import tempfile

from cases import make as basic
from extra_cases import make as extra
from update_cases import make as updates
from fanin_cases import make as fanin

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/waveform'))
from reader import read, bit_timeline

parser = argparse.ArgumentParser()
parser.add_argument('compiler', type=Path)
parser.add_argument('out', type=Path)
parser.add_argument('--case', action='append')
args = parser.parse_args()
compiler, out = args.compiler.resolve(), args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
report_out=out
out=Path(tempfile.mkdtemp(prefix='run-',dir=out))
references = json.loads((Path(__file__).with_name('expected.json')).read_text())['cases']
references.update(json.loads((Path(__file__).with_name('expected-updates.json')).read_text())['cases'])
results = {}
for prefix, generate in [('basic', basic), ('extra', extra), ('updates', updates), ('fanin', fanin)]:
    base = out / prefix
    generated = generate(base)
    for name in generated:
        if args.case and name not in args.case:
            continue
        w = base / name
        # Native XMR expressions are not implemented. Preserve original stimuli,
        # structure/library/SDF; monitor output ports and decode receiving pins
        # from the waveform dictionary instead. Do not claim identical raw TB.
        original_tb = (w / 'tb.v').read_text()
        lines = original_tb.splitlines()
        monitors = [i for i, line in enumerate(lines) if line.startswith('always @')]
        assert len(monitors) == 1
        lines[monitors[0]] = 'always @(x or y) $display("TRACE t=%0t x=%b y=%b",$time,x,y);'
        native_tb = w / 'native-tb.v'
        native_tb.write_text('\n'.join(lines) + '\n')

        def run(command, label):
            p = subprocess.run(list(map(str, command)), cwd=w, capture_output=True, text=True, timeout=180)
            (w / (label + '.log')).write_text(p.stdout + p.stderr)
            assert p.returncode == 0, (name, label, p.stderr)
            assert not any(s in p.stderr for s in ['AddressSanitizer', 'runtime error:', 'DEADLYSIGNAL'])
            return p.stdout

        run([compiler, '--gate-netlist', w / 'net.v', '--gate-top', 'dut', '--liberty', w / 'cells.lib',
             '--gate-models', w / 'cells.v', '--sdf-annotate', w / 'delay.sdf', native_tb,
             '--wave-support', '--emit-ir', w / 'ir.json', '-o', w / 'native'], 'compile')
        ir = json.loads((w / 'ir.json').read_text())
        assert ir['gate_design']['interconnect_pins'] > 0
        decoded = []
        traces = []
        for fmt in ['vcd', 'dwf']:
            wave = w / ('native.' + fmt)
            wave.unlink(missing_ok=True)
            traces.append(run([w / 'native', '--waveform', wave, '--wave-format', fmt], fmt))
            decoded.append(bit_timeline(*read(wave)))
        assert traces[0] == traces[1] and decoded[0] == decoded[1]
        bits = decoded[0]
        expected = {tuple(record['path']) + (record['bit'],): record['changes'] for record in references[name]['bits']}
        for pin in ['x', 'y']:
            key = ('top', pin, None)
            assert json.loads(json.dumps(bits[key])) == expected[key], (name, pin, bits[key], expected[key])
        private_pins = [key for key in bits if len(key) >= 5 and key[-2] == 'A']
        assert len(private_pins) == ir['gate_design']['interconnect_pins']
        for key in private_pins:
            assert json.loads(json.dumps(bits[key])) == expected[key], (name, key, bits[key], expected[key])
        results[name] = dict(status='PASS', interconnect_pins=len(private_pins),
            trace=traces[0].splitlines(), scope='Unchanged structural/library/SDF/stimuli; native output monitor replaces unsupported XMR; all output and private-pin settled bits match frozen VCS, VCD/DWF complete native streams match.')
        print('PASS compiled INTERCONNECT + IOPATH + VCD/DWF', name, flush=True)
report=dict(status='PASS', run_directory=str(out), cases=results)
(out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
(report_out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
