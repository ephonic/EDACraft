"""Hierarchy/width oracles and actual generated speculative dump side effects."""
from pathlib import Path
import json
import importlib.util
import sys

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'tests/waveform'))
from reader import read, declarations, timeline

def exercise(compiler, out, run, same, report):
    work = out / 'escaped-wide'; work.mkdir()
    source = work / 'top.v'
    source.write_text('''`timescale 1ps/1ps
module leaf(input [1:0] a,output [257:0] q);
  parameter N=129;
  assign q={N{a}};
endmodule
module top;
  reg [1:0] \\a.b ; wire [257:0] result;
  leaf \\u.dot (\\a.b ,result);
  initial begin \\a.b =2'bxz; #2 \\a.b =2'b10; #2 \\a.b =2'bz1; #2 $finish; end
  initial begin $dumpfile("wide.vcd"); $dumpvars(0,top.\\u.dot .q,\\a.b ); end
endmodule
''')
    exe = work / 'simv'
    run([compiler, source, '-o', exe], work, 'compile')
    reference = None
    for label, flags in [('vcd', []), ('raw', ['--waveform', 'wide.dwf', '--wave-format', 'dwf', '--wave-codec', 'raw']),
                          ('zstd', ['--waveform', 'wide.dwf', '--wave-format', 'dwf', '--wave-compression-jobs', '4'])]:
        w = work / label; w.mkdir(); run([exe, *flags], w, 'run')
        wave = w / ('wide.vcd' if label == 'vcd' else 'wide.dwf')
        meta, events = read(wave); names = declarations(meta)
        assert set(names) == {('top', 'u.dot', 'q'), ('top', 'a.b')}, names
        lines = timeline(meta, events)
        def packed(text):
            a = b = 0
            for bit in text:
                a = (a << 1) | (bit in '1x'); b = (b << 1) | (bit in 'xz')
            return a,b
        assert lines[('top', 'u.dot', 'q')][2] == [(t, packed(s * 129)) for t,s in [(0,'xz'),(2,'10'),(4,'z1')]]
        assert lines[('top', 'a.b')][2] == [(t, packed(s)) for t,s in [(0,'xz'),(2,'10'),(4,'z1')]]
        if reference: same(reference, wave)
        else: reference = wave
    report['escaped_components_wide_replication'] = 'PASS'

    glitch = out / 'first-timestamp'; glitch.mkdir(); source = glitch / 'top.v'; exe = glitch / 'simv'
    source.write_text('`timescale 1ps/1ps\nmodule top;reg a;initial begin $dumpfile("first.vcd");'
                      '$dumpvars(0,a);a=0;a=1;a=0;#1 $finish;end endmodule\n')
    run([compiler, source, '-o', exe], glitch, 'compile')
    for mode in ['ordered', 'settled']:
        reference = None
        for kind in ['vcd', 'dwf']:
            w = glitch / (mode+'-'+kind); w.mkdir(); wave = w / ('first.'+kind)
            run([exe, '--waveform', wave, '--wave-format', kind, '--wave-mode', mode], w, 'run')
            values = [(t,v) for t,k,v in read(wave)[1] if k == 'value']
            expected = [(0,(0,(1,1))),(0,(0,(0,0))),(0,(0,(1,0))),(0,(0,(0,0)))] if mode=='ordered' else [(0,(0,(0,0)))]
            assert values == expected, (mode, values)
            if reference: same(reference, wave)
            else: reference = wave
    report['first_timestamp_ordered_changes'] = 'PASS'

    # Detection examines actual preprocessed code tokens, excluding quoted,
    # escaped and ordinary identifiers that only contain a dump task's spelling.
    w = out / 'token-detection'; w.mkdir()
    source = w / 'top.v'
    source.write_text('module top; reg x$dumpvars; reg \\$dumpfile ; initial begin '
                      'x$dumpvars=0; \\$dumpfile =0; $display("$dumpvars $dumpfile"); '
                      '/* $dumpon */ // $dumpoff\n $finish; end endmodule\n')
    cpp = w / 'model.cpp'
    run([compiler, source, '--emit-only', '--emit-cpp', cpp], w, 'compile')
    assert '#define DSIM_WAVE_ENABLED 1\n' not in cpp.read_text()
    assert '#define DSIM_DUMP_TASKS_ENABLED 1\n' not in cpp.read_text()
    source = w / 'macro.v'
    source.write_text('`define START $dumpvars(0,top)\nmodule top; reg a; initial begin a=0; `START; #1 $finish; end endmodule\n')
    run([compiler, source, '--emit-only', '--emit-cpp', w / 'macro.cpp'], w, 'macro')
    assert '#define DSIM_DUMP_TASKS_ENABLED 1\n' in (w / 'macro.cpp').read_text()
    report['automatic_detection'] = 'PASS'

    malformed = {
        'missing-scope': '$dumpvars(0,top.missing);',
        'missing-signal': '$dumpvars(0,top.a.missing);',
        'empty-file': '$dumpfile("");',
        'no-file': '$dumpfile();',
        'numeric-file': '$dumpfile(1);',
        'all-args': '$dumpall(1);',
        'off-args': '$dumpoff(1);',
        'on-args': '$dumpon(1);',
        'unknown-depth': "$dumpvars(32'bx,top);",
        'large-depth': '$dumpvars(10001,top);',
        'expression-target': '$dumpvars(0,a+1);',
        'select-target': '$dumpvars(0,a[0]);',
    }
    rejected = out / 'rejected'; rejected.mkdir()
    for name, call in malformed.items():
        w = rejected / name; w.mkdir(); source = w / 'top.v'
        source.write_text('module top; reg [1:0] a; initial begin '+call+' end endmodule\n')
        run([compiler, source, '--emit-only', '--emit-cpp', w / 'model.cpp'], w, 'compile', False)
        assert not (w / 'model.cpp').exists()
    report['invalid_tasks_rejected'] = len(malformed)
    for name, value in [('unknown', "32'bx"), ('large', "32'd10001")]:
        w = rejected / ('dynamic-'+name); w.mkdir(); source = w / 'top.v'; exe = w / 'simv'
        source.write_text('module top;reg [31:0] depth;initial begin depth='+value+'; $dumpvars(depth,top); #1 $finish; end endmodule\n')
        run([compiler, source, '-o', exe], w, 'compile')
        failed = run([exe], w, 'run', False)
        assert '$dumpvars depth must be a known integer' in failed.stderr
        assert not (w / 'verilog.dump').exists()
    report['invalid_dynamic_depths_rejected'] = 2
    protected = out / 'protected'; protected.mkdir(); existing = protected / 'vcs.vcd'
    existing.write_text('existing waveform must survive\n')
    run([out / 'all/simv'], protected, 'run', False)
    assert existing.read_text() == 'existing waveform must survive\n'
    report['existing_file_protected'] = True

    spec = importlib.util.spec_from_file_location('root_input_cases', root / 'tests/sdf_root_input/cases.py')
    root_cases = importlib.util.module_from_spec(spec); spec.loader.exec_module(root_cases)
    sdf_inputs = out / 'sdf-inputs'; root_cases.make(sdf_inputs)
    golden = json.loads((root / 'tests/sdf_root_input/expected.json').read_text())['cases']
    from run_flow import physical_bits
    sdf_captures = sdf_bits = 0
    for name in ['root-buffer', 'internal-three']:
        src = sdf_inputs / name; source = src / 'dump.v'
        text = (src / 'tb.v').read_text()
        source.write_text(text.replace('endmodule', 'initial begin $dumpfile("sdf.vcd"); $dumpvars(0,top.d); end\nendmodule', 1))
        reference = None
        for backend, flags in [('generic', []), ('jobs', ['--gate-scalar-timing', '--gate-sdf-jobs', '--gate-fold-zero-inputs']),
                               ('wheel', ['--gate-scalar-timing', '--gate-sdf-jobs', '--gate-fold-zero-inputs', '--time-wheel'])]:
            w = out / ('sdf-'+name+'-'+backend); w.mkdir(); exe = w / 'simv'
            run([compiler, '--gate-netlist', src / 'net.v', '--gate-top', 'dut', '--liberty', src / 'cells.lib',
                 '--gate-models', src / 'cells.v', '--sdf-annotate', src / 'delay.sdf', source, *flags, '-o', exe], w, 'compile')
            for kind, args in [('vcd', []), ('dwf', ['--waveform', 'sdf.dwf', '--wave-format', 'dwf', '--wave-compression-jobs', '4'])]:
                target = w / kind; target.mkdir(); result = run([exe, *args], target, 'run')
                assert [line for line in result.stdout.splitlines() if line.startswith('TRACE ')] == golden[name]['trace']
                wave = target / ('sdf.'+kind); bits = physical_bits(wave)
                expected = {tuple(bit['path'])+(bit['bit'],):bit['changes'] for bit in golden[name]['native_bits']
                            if bit['path'][:2] == ['top','d']}
                assert expected and set(bits) == set(expected), (name, set(bits), set(expected))
                for key, changes in expected.items():
                    assert json.loads(json.dumps(bits[key])) == changes, (name, backend, key)
                    sdf_bits += 1
                if reference: same(reference, wave)
                else: reference = wave
                sdf_captures += 1
    report['sdf_task_captures'] = sdf_captures
    report['sdf_vendor_physical_comparisons'] = sdf_bits

    config = {line.split('=',1)[0].split(':',1)[0]: line.split('=',1)[1] for line in
              (compiler.parent / 'CMakeCache.txt').read_text().splitlines() if '=' in line and not line.startswith('//')}
    captures = comparisons = 0
    for name in ['all', 'late', 'off-on-all']:
        w = out / (name + '-transactions'); w.mkdir()
        code = (out / name / 'model.cpp').read_text()
        assert code.count('\ns.run();\n') == 1
        marker = 'vcs.vcd'
        bodies = {
            'boundary': '\ns.run_until(5);s.run_until(9);s.run();\n',
            'rollback': '''
if(s.predict_until(5,[](Sim& probe){
 for(size_t i=0;i<probe.signals.size();++i)if(!probe.signals[i].net)probe.set(int(i),V::x(probe.signals[i].value.w));
},[&](const Sim&){
 if(std::filesystem::exists(argv[2]))throw std::runtime_error("speculative file created before commit");
 return false;
},[](Sim&){}))throw std::runtime_error("missing rollback");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback count");
if(!s.predict_until(9,[](Sim&){},[](const Sim&){return true;},[](Sim&){}))throw std::runtime_error("missing commit");
s.run();
''',
            'commit': '''
if(!s.predict_until(5,[](Sim&){},[&](const Sim&){
 if(std::filesystem::exists(argv[2]))throw std::runtime_error("speculative file created before commit");
 return true;
},[](Sim&){}))throw std::runtime_error("missing initial commit");
s.run_until(9);s.run();
'''
        }
        variants = {}
        for variant, body in bodies.items():
            cpp = w / (variant + '.cpp'); exe = w / variant
            cpp.write_text('#include <filesystem>\n' + code.replace('\ns.run();\n', body))
            run(['c++', '-std=c++17', '-O2', '-pthread', '-I'+config['DSIM_ZSTD_INCLUDE'], cpp,
                 config['DSIM_ZSTD_LIBRARY'], '-o', exe], w, variant + '-compile')
            variants[variant] = exe
        references = {}
        for variant, exe in variants.items():
            for mode in ['ordered', 'settled']:
                for kind, flags in [('vcd', ['--wave-format', 'vcd']),
                                    ('raw', ['--wave-format', 'dwf', '--wave-codec', 'raw']),
                                    ('zstd', ['--wave-format', 'dwf', '--wave-compression-jobs', '4'])]:
                    label = variant+'-'+mode+'-'+kind; target = w / label; target.mkdir()
                    dest = target / ('vcs.vcd' if kind == 'vcd' else 'capture.dwf')
                    # Default source filename remains visible to the validator;
                    # DWF uses an explicit output, which must also stay absent.
                    run([exe, '--waveform', dest, '--wave-mode', mode, '--wave-block-events', '3', *flags], target, 'run')
                    if kind != 'vcd':
                        assert not (target / marker).exists()
                    key = mode
                    if key in references: same(references[key], dest); comparisons += 1
                    else: references[key] = dest
                    captures += 1
    report['transaction_captures'] = captures
    report['transaction_complete_comparisons'] = comparisons
    assert captures == 54 and comparisons == 48
