"""Compare actual native captures to independently bounded serial kernels."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/waveform'))
from reader import read

binary, base = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
base.mkdir(parents=True, exist_ok=True)
out = Path(tempfile.mkdtemp(prefix='run-', dir=base))
cases = []
for mode in ['ordered', 'settled']:
    expected = None
    for variant in ['reference', '1', '2', '4']:
        waves = {}
        stdout = None
        for codec in ['vcd', 'raw', 'zstd']:
            work = out / (mode + '-' + variant + '-' + codec)
            work.mkdir()
            command = [str(binary), variant, str(work), mode, codec]
            result = subprocess.run(command, text=True, capture_output=True, timeout=60)
            (work / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
            (work / 'stdout').write_text(result.stdout)
            (work / 'stderr').write_text(result.stderr)
            assert result.returncode == 0, (command, result.stderr)
            if stdout is None:
                stdout = result.stdout
            assert stdout == result.stdout
            captures = []
            for i in range(4):
                path = work / ('p' + str(i) + ('.vcd' if codec == 'vcd' else '.dwf'))
                capture = read(path)
                assert max(t for t, _, _ in capture[1]) <= (5 if i <= 1 else 4)
                captures.append(capture)
            if waves:
                assert captures == waves['vcd'], (mode, variant, codec)
            waves[codec] = captures
        current = (stdout, waves['vcd'])
        if expected is None:
            expected = current
        assert current == expected, (mode, variant)
        assert len(stdout.splitlines()) == 22
        cases.append(dict(mode=mode, variant=variant, codecs=['vcd', 'raw', 'zstd'], status='PASS'))
        print('PASS native global finish full stdout/VCD/DWF', mode, variant, flush=True)
(base / 'results.json').write_text(json.dumps(dict(status='PASS', directory=str(out), cases=cases,
    captures=96, independently_bounded_serial=True), indent=2) + '\n')
