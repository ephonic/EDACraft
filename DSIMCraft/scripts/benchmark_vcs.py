#!/usr/bin/env python3
"""Same-host scaling baseline for arithmetic loops and clock/edge/NBA scheduling.

Run after sourcing the VCS environment. Reports actual gaps, with independent
expected results; these workloads do not cover large netlists or timing simulation.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import statistics
import subprocess

from compare_vcs import ROOT, timed


def lcg(count):
    # Compose affine transforms by exponentiation, independent of simulator loops.
    multiplier, increment = 1664525, 1013904223
    result_multiplier, result_increment = 1, 0
    mask = (1 << 32)-1
    while count:
        if count & 1:
            result_multiplier = result_multiplier*multiplier & mask
            result_increment = (result_increment*multiplier+increment) & mask
        increment = increment*(multiplier+1) & mask
        multiplier = multiplier*multiplier & mask
        count >>= 1
    return result_increment


def workload(name, count, fanout=32):
    if name == 'arithmetic':
        source = f'''module top;
  reg [31:0] i,q;
  initial begin
    q=0;
    for(i=0;i<32'd{count};i=i+32'd1)
      q=q*32'd1664525+32'd1013904223;
    $display("TRACE q=%h iterations=%0d",q,i);
    $finish;
  end
endmodule
'''
        expected = [f'TRACE q={lcg(count):08x} iterations={count}']
    elif name == 'clocked':
        source = f'''module top;
  reg clk;
  reg [31:0] q;
  initial begin clk=0; forever #1 clk=~clk; end
  always @(posedge clk) q<=q+32'd1;
  initial begin
    q=0;
    #0;
    repeat(32'd{count}) @(negedge clk);
    #0 $display("TRACE q=%0d time=%0d",q,$time);
    $finish;
  end
endmodule
'''
        expected = [f'TRACE q={count} time={count*2}']
    else:
        source = 'module top;\n  reg clk;\n'
        source += ''.join(f'  reg [31:0] q{i};\n' for i in range(fanout))
        source += '  wire [63:0] checksum;\n'
        source += '  assign checksum='+ '+'.join(f"{{32'd0,q{i}}}" for i in range(fanout))+';\n'
        source += '  initial begin clk=0; forever #1 clk=~clk; end\n'
        source += ''.join(f"  always @(posedge clk) q{i}<=q{i}+32'd{i+1};\n" for i in range(fanout))
        source += '  initial begin\n'+''.join(f'    q{i}=0;\n' for i in range(fanout))
        source += f"    #0;\n    repeat(32'd{count}) @(negedge clk);\n"
        source += '    #0 $display("TRACE checksum=%h time=%0d",checksum,$time);\n    $finish;\n  end\nendmodule\n'
        checksum=sum((count*(i+1)) & 0xffffffff for i in range(fanout))
        expected = [f'TRACE checksum={checksum:016x} time={count*2}']
    return source, expected


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dsim', type=Path, default=ROOT/'build/dsim')
    ap.add_argument('--baseline-dsim', type=Path, help='Also compile/run an unchanged earlier dsim on each input')
    ap.add_argument('--output', type=Path, default=ROOT/'build/vcs-benchmark')
    ap.add_argument('--iterations', type=int, nargs='+', default=[100000, 1000000])
    ap.add_argument('--repeat', type=int, default=3)
    ap.add_argument('--workload', action='append', choices=['arithmetic','clocked','fanout'], help='Repeatable; defaults to arithmetic and clocked')
    ap.add_argument('--fanout', type=int, default=32, help='Number of independently clocked processes in fanout workload')
    args = ap.parse_args()
    if args.repeat < 1 or any(n < 1 or n >= 2**32 for n in args.iterations):
        ap.error('repeat must be positive; iterations must be in 1..2**32-1')
    if not 1 <= args.fanout <= 1024:
        ap.error('fanout must be in 1..1024')
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    version = subprocess.run(['vcs', '-full64', '-ID'], capture_output=True, text=True, timeout=30)
    if version.returncode:
        raise RuntimeError(version.stdout+version.stderr)
    report = {'host': platform.node(), 'platform': platform.platform(),
              'utc': datetime.now(timezone.utc).isoformat(),
              'cpu': platform.processor(),
              'dsim_version': subprocess.check_output([str(args.dsim.resolve()), '--version'], text=True).strip(),
              'vcs_version': version.stdout+version.stderr,
              'cxx_version': subprocess.check_output(['c++', '--version'], text=True),
              'vcs_flags': ['-full64', '-sverilog', '-top', 'top'],
              'dsim_flags': ['--top', 'top'], 'native_flags': ['-std=c++17', '-O2'],
              'repeat': args.repeat, 'warmup_runs_per_tool': 1,
              'note': 'Same-host microbenchmarks; elapsed time includes process startup. No waveform output. Compilation measured separately. Does not establish broad VCS performance parity.',
              'cases': {}}
    if args.baseline_dsim:
        report['baseline_dsim_version'] = subprocess.check_output([str(args.baseline_dsim.resolve()), '--version'], text=True).strip()
    try:
        for name in dict.fromkeys(args.workload or ['arithmetic','clocked']):
            for count in args.iterations:
                label = f'fanout{args.fanout}' if name=='fanout' else name
                key = f'{label}-{count}'; work = out/key; work.mkdir(exist_ok=True)
                text, expected = workload(name, count, args.fanout)
                source = work/'input.v'; source.write_text(text)
                native, vcs = work/'dsim_simv', work/'vcs_simv'
                record = {'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                          'workload': name, 'iterations': count, 'trace': expected}
                if name=='fanout': record['fanout'] = args.fanout
                report['cases'][key] = record
                record['dsim_compile'], _ = timed([args.dsim.resolve(), '--top', 'top', source, '-o', native], work, 'dsim-compile')
                record['vcs_compile'], _ = timed(['vcs', '-full64', '-sverilog', '-top', 'top', source, '-o', vcs], work, 'vcs-compile')
                limit=str(max(10000000, count*(100+(args.fanout*8 if name=='fanout' else 0))))
                commands = {'dsim': [native, '--max-events', limit], 'vcs': [vcs]}
                if args.baseline_dsim:
                    baseline=work/'baseline_dsim_simv'
                    record['baseline_dsim_compile'], _ = timed([args.baseline_dsim.resolve(), '--top', 'top', source, '-o', baseline], work, 'baseline_dsim-compile')
                    commands['baseline_dsim'] = [baseline, '--max-events', limit]
                record['run_commands'] = {tool: [str(a) for a in command] for tool, command in commands.items()}
                for tool, command in commands.items():
                    _, trace = timed(command, work, f'{tool}-warmup')
                    if trace != expected:
                        raise AssertionError(f'{key} {tool} warmup: {trace} != {expected}')
                    record[f'{tool}_runs'] = []
                for i in range(args.repeat):
                    order=list(commands); shift=i%len(order)
                    for tool in order[shift:]+order[:shift]:
                        stem = f'{tool}-run-{i}'
                        stats, trace = timed(commands[tool], work, stem)
                        if trace != expected:
                            raise AssertionError(f'{key} {tool}: {trace} != {expected}')
                        time_text = (work/f'{stem}.time').read_text()
                        for label, field in [('User time (seconds)', 'user_seconds'), ('System time (seconds)', 'system_seconds')]:
                            match = re.search(re.escape(label)+r': ([0-9.]+)', time_text)
                            stats[field] = float(match[1]) if match else None
                        record[f'{tool}_runs'].append(stats)
                for tool in commands:
                    record[f'{tool}_median_seconds'] = statistics.median(r['wall_seconds'] for r in record[f'{tool}_runs'])
                record['dsim_over_vcs_wall_ratio'] = record['dsim_median_seconds']/record['vcs_median_seconds']
                if args.baseline_dsim:
                    record['baseline_over_dsim_wall_ratio'] = record['baseline_dsim_median_seconds']/record['dsim_median_seconds']
                record['status'] = 'PASS'
                (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')
                print(f'PASS {key}: dsim={record["dsim_median_seconds"]:.4f}s VCS={record["vcs_median_seconds"]:.4f}s ratio={record["dsim_over_vcs_wall_ratio"]:.3f}', flush=True)
    except Exception as e:
        report['failure'] = str(e)
        raise
    finally:
        (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
