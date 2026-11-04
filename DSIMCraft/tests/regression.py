#!/usr/bin/env python3
"""Compile real Verilog, execute native models, compare independent expectations."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

CASES = {
    'scheduler_wait_sites': ['TRACE pos count=1 t=1', 'TRACE high_bit count=2 t=3',
                             'TRACE either count=3 t=5', 'TRACE neg count=4 t=6',
                             'TRACE pos count=5 t=7', 'TRACE high_bit count=6 t=9',
                             'TRACE either count=7 t=11', 'TRACE neg count=8 t=12',
                             'TRACE done count=8'],
    'scheduler_regions': ['TRACE inactive a=0 b=0 q=00', 'TRACE still_inactive a=0 b=0 q=00',
                          'TRACE batch a=1 b=2 q=a5',
                          'TRACE committed a=1 b=2 q=a5 observations=1',
                          'TRACE batch a=3 b=4 q=a5', 'TRACE second a=3 b=4 observations=2'],
    'control_loops': ['TRACE for q=45 i=5 j=3', 'TRACE while q=51 once=1',
                       'TRACE repeat q=59 count=0 i=3'],
    'control_timing': ['TRACE inactive q=0 t=1', 'TRACE committed q=1 t=2',
                        'TRACE inactive q=1 t=3', 'TRACE committed q=2 t=4',
                        'TRACE inactive q=2 t=5', 'TRACE committed q=3 t=6',
                        'TRACE for q=7 t=8', 'TRACE do q=10 t=11',
                        'TRACE while q=8 t=14', 'TRACE nested q=12 t=15'],
    'control_case': ['TRACE exact=2', 'TRACE casez=5', 'TRACE casex=7',
                      'TRACE concat=11', 'TRACE width=15', 'TRACE context=24', 'TRACE fill=27',
                      'TRACE hold=17', 'TRACE selector_wild=19', 'TRACE nested=21 selector=0'],
    'control_comb': ['TRACE y=12', 'TRACE y=15', 'TRACE y=6', 'TRACE y=3'],
    'control_case_matrix': json.loads((Path(__file__).parent/'cases/control_case_matrix.expected.json').read_text()),
    'lvalue_matrix': json.loads((Path(__file__).parent/'cases/lvalue_matrix.expected.json').read_text()),
    'lvalue_blocking': ['TRACE swap=69', 'TRACE q=xz101001 shifted=a5 a=d b=9 flag=0 overlap=0100',
                         'TRACE context=10', 'TRACE fill=ff wide=8000000000000002'],
    'lvalue_nba': ['TRACE inactive q=01 r=01 a=1 b=2 wide=0000000000000000',
                   'TRACE committed q=3e r=11 a=2 b=1 wide=80000005deadcafe flag=0', 'TRACE ordered q=fe'],
    'lvalue_nets': ['TRACE bus=1010xx01 split=5a dup=x edge=8000000000000001',
                    'TRACE bus=101010zz split=5a', 'TRACE bus=111x10zz split=5f edge=0000000000000001'],
    'port_parts': ['TRACE bus=01zzzzzz seen=zz01 state=dz6 read=b input=10zz repeat=x/10 wide=0za concat_input=1zz0',
                   'TRACE bus=xxzzzz10 seen=10xx', 'TRACE bus=10zzzz10 seen=1010',
                   'TRACE bus=zzzzzzzz seen=zzzz'],
    'hierarchy_defaults': ['TRACE connected=0 named=z implicit=f top=z floating=x',
                           'TRACE connected=5 named=z implicit=f'],
    'hierarchy': ['TRACE small=f large=11 nested=10', 'TRACE small=0 large=02 nested=01'],
    'hierarchy_nets': ['TRACE bus=z seen=zz output=1 read=1 shift=a',
                       'TRACE bus=0 seen=00 output=x read=x', 'TRACE bus=x seen=xx',
                       'TRACE bus=1 seen=11', 'TRACE bus=z seen=zz output=z read=z'],
    'hierarchy_ports': ['TRACE y=0c open=zzzz expr=9 var=c const=b select=a concat=2 open_var=zzzz',
                        'TRACE y=03 open=zzzz expr=6 var=3'],
    'hierarchy_events': ['TRACE a=15 b=21', 'TRACE a=0 b=22'],
    'ports': ['TRACE q=9 fill=ff'],
    'declarations': ['TRACE q=3 y=3', 'TRACE q=5 y=5'],
    'counter': ['TRACE q=1 plus=2', 'TRACE q=3 plus=4', 'TRACE q=5 plus=6', 'TRACE q=7 plus=8'],
    'four_state': ['TRACE a=10xz and=10x0 or=101x mux=10xx eq=x case=0', 'TRACE and=0000 or=xxxx mux=zzzz'],
    'gates': ['TRACE n=0 y=1 z=0 bus=0', 'TRACE n=0 y=1 z=1 bus=x', 'TRACE n=1 y=0 z=0 bus=1', 'TRACE n=x y=x z=x bus=1'],
    'unnamed_gates': ['TRACE slow=1000 fast=1000', 'TRACE slow=0111 fast=0111',
                      'TRACE slow=0000 fast=0000', 'TRACE slow=xxxx fast=xxxx',
                      'TRACE slow=1000 fast=1000'],
    'nba': ['TRACE inactive a=1 b=2', 'TRACE committed a=2 b=1 seen=1', 'TRACE swapped a=1 b=2'],
    'widths': ['TRACE sum=100 nibble=1111 pair=ff01 wrap=0000000000000000'],
    'star': ['TRACE y=0', 'TRACE y=1', 'TRACE y=0'],
    'edges': ['TRACE pos=2 neg=4 both=6'],
    'expressions': ['TRACE add=243 sub=237 mul=208 div=80 mod=0 shl=80 shr=1e',
                    'TRACE cmp=0101 logic=x1x red=01x inv=x111',
                    'TRACE equal=0 case=0 unequal=1'],
}

# VCS is the compatibility reference. Keep observed Icarus differences in
# overlapping concatenations, default ports and output-net readback explicit.
ICARUS_EXPECTED = {
    'lvalue_matrix': json.loads((Path(__file__).parent/'cases/lvalue_matrix.icarus.json').read_text()),
    'lvalue_blocking': [CASES['lvalue_blocking'][0],
                        'TRACE q=xz101001 shifted=a5 a=d b=9 flag=1 overlap=0110',
                        *CASES['lvalue_blocking'][2:]],
    'lvalue_nba': [CASES['lvalue_nba'][0],
                   'TRACE committed q=3e r=11 a=2 b=1 wide=80000005deadcafe flag=1',
                   *CASES['lvalue_nba'][2:]],
    'port_parts': ['TRACE bus=01zzzzzz seen=zz01 state=dz6 read=z input=10zz repeat=x/10 wide=0za concat_input=1zz0',
                   *CASES['port_parts'][1:]],
    'hierarchy_defaults': ['TRACE connected=0 named=f implicit=f top=z floating=z',
                           'TRACE connected=5 named=f implicit=f'],
}

ICARUS_NOTES = {
    'lvalue_matrix': 'Overlapping variable concatenation order differs from VCS; see validation/m2-lvalues/README.md',
    'lvalue_blocking': 'Overlapping variable concatenation order differs from VCS; see validation/m2-lvalues/README.md',
    'lvalue_nba': 'Overlapping variable concatenation order differs from VCS; see validation/m2-lvalues/README.md',
    'hierarchy_defaults': 'Explicit open default port and root variable input differ from VCS; see validation/m2-hierarchy/README.md',
    'port_parts': 'Selected/concatenated output net readback differs from VCS; see validation/m2-lvalues/README.md',
}

def run(args, cwd=None, ok=True):
    p = subprocess.run([str(a) for a in args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    if ok and p.returncode:
        raise RuntimeError(f'{args}: exit {p.returncode}\n{p.stdout}')
    return p

def traces(text):
    return [s for s in text.splitlines() if s.startswith('TRACE ')]

def check_ir(case, ir):
    assert ir['schema'] == 'dsim.elaboration.v1' and ir['frontend'] == 'rtl'
    scopes = {s['path']: s for s in ir['scopes']}
    def signal(path, name): return scopes[path]['signals'][name]['id']
    def param(path, name): return int(scopes[path]['parameters'][name]['bits'], 2)
    for scope in scopes.values():
        for sig in scope['signals'].values():
            assert 0 <= sig['id'] < ir['signal_count']
    if case == 'hierarchy':
        assert set(scopes) == {'top', 'top.u4', 'top.u8', 'top.wrap', 'top.wrap.inner'}
        assert param('top.u4','W') == 4 and param('top.u8','W') == 8
        assert param('top.u4','STEP') == 1 and param('top.wrap.inner','STEP') == 2
        assert signal('top.u4','a') != signal('top.u8','a')
        assert signal('top','nested') == signal('top.wrap.inner','y')
    if case == 'hierarchy_nets':
        assert signal('top','bus') == signal('top.e0','bus') == signal('top.e1','bus')
        assert signal('top','ob') == signal('top.rb','bus')
        assert scopes['top.sh']['signals']['a']['lsb'] == 4
    if case == 'port_parts':
        assert ir['net_bit_connections']
        ports = {(p['scope'],p['port']): p for p in ir['ports']}
        assert ports['top.wrap','bus']['binding'] == 'connected_bits'
        assert ports['top.rb','y']['binding'] == 'connected_bits'
        assert ports['top.nw','q']['binding'] == 'adapter'
        assert len(ports['top.st','q']['actual_parts']) == 2
    if case == 'hierarchy_events':
        assert param('top.g.c0','START') == 14 and param('top.g.c1','START') == 20
        assert signal('top.g.c0','q') != signal('top.g.c1','q')
    if case == 'unnamed_gates':
        assert set(scopes) == {'top', 'top.slow', 'top.slow.u', 'top.fast', 'top.fast.u'}
        assert param('top.slow.u','D') == 3 and param('top.fast.u','D') == 1
        assert signal('top.slow.u','y') != signal('top.fast.u','y')

def main():
    compiler = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    source_dir = Path(__file__).parent / 'cases'
    results = {}
    for case, expected in CASES.items():
        work = output / case
        work.mkdir(exist_ok=True)
        source = (source_dir / f'{case}.v').resolve()
        native = work / 'simv'
        compiled = run([compiler, source, '--emit-ir', work/'ir.json', '-o', native])
        check_ir(case, json.loads((work/'ir.json').read_text()))
        execution = run([native])
        (work / 'compile.log').write_text(compiled.stdout)
        (work / 'run.log').write_text(execution.stdout)
        actual = traces(execution.stdout)
        assert actual == expected, f'{case}:\nexpected {expected}\nactual   {actual}'
        if shutil.which('iverilog'):
            run(['iverilog', '-g2012', '-s', 'top', '-o', work/'iv', source])
            iv = run(['vvp', work/'iv'])
            (work / 'iverilog.log').write_text(iv.stdout)
            assert traces(iv.stdout) == ICARUS_EXPECTED.get(case, actual), f'{case}: Icarus mismatch {iv.stdout}'
        results[case] = {'trace': actual, 'status': 'PASS'}
        if case in ICARUS_EXPECTED:
            results[case]['icarus_difference'] = ICARUS_NOTES[case]
        print(f'PASS {case}')
    negatives = {
        'cast': ("module top; reg [7:0] q; initial q=0'(8'hff); endmodule", 'cast width must be'),
        'specify': ('module top; specify endspecify endmodule', 'specify timing'),
        'syntax': ('module top; reg a; initial a=; endmodule', 'syntax error'),
        'unknown_module': ('module top; missing u(); endmodule', 'unresolved module'),
        'output_variable_conflict': ('module c(output y); assign y=1; endmodule module top; reg a; c u(a); initial a=0; endmodule', 'variable port driver conflicts'),
        'output_concat_variable_conflict': ('module c(output [1:0] y); assign y=2; endmodule module top; wire a; reg b; c u({a,b}); initial b=0; endmodule', 'variable port driver conflicts'),
        'inout_width': ('module c(inout [1:0] a); endmodule module top; wire a; c u(a); endmodule', 'equal-width net lvalues'),
        'unknown_port': ('module c(input a); endmodule module top; c u(.missing(1)); endmodule', 'semantic analysis failed'),
        'duplicate_port': ('module c(input a); endmodule module top; c u(.a(1),.a(0)); endmodule', 'semantic analysis failed'),
        'unknown_parameter': ('module c #(parameter W=1)(); endmodule module top; c #(.BAD(4)) u(); endmodule', 'semantic analysis failed'),
        'oversized': ('module top; reg [1048576:0] q; endmodule', 'packed ranges'),
        'unsupported_task': ('module top; initial $monitor("x"); endmodule', 'unsupported system task'),
        'timescale': ('`default_nettype none\nmodule top; endmodule', 'preprocessing directives'),
        'bad_format': ('module top; initial $display("%s",1); endmodule', 'supported formats'),
        'incomplete_unnamed_gate': ('module top; wire q; buf(q); endmodule', 'unsupported gate port count'),
        'oversized_concat_lvalue': ('module top; reg [524287:0] q; reg b; initial {q,q,b}=0; endmodule', 'target width exceeds'),
        'procedural_net_piece': ('module top; wire [7:0] q; initial q[0]=1; endmodule', 'procedural assignment to a net'),
        'continuous_variable_piece_conflict': ('module top; reg [7:0] q; assign q[0]=1; initial q[0]=0; endmodule', 'variable port driver conflicts'),
        'bad_for_header': ('module top; reg [7:0] i; initial for(i+1;i<3;i=i+1) ; endmodule', 'semantic analysis failed'),
        'duplicate_default': ('module top; initial case(1) default: ; default: ; endcase endmodule', 'semantic analysis failed'),
    }
    for case, (text, error) in negatives.items():
        source = output / f'negative_{case}.v'
        source.write_text(text+'\n')
        p=run([compiler, source, '-o', output/f'negative_{case}'], ok=False)
        assert p.returncode != 0 and error in p.stdout, f'{case}: {p.stdout}'
        assert not (output/f'negative_{case}').exists()
        print(f'PASS reject {case}')
    empty = output/'empty.v'
    empty.write_text('module child; endmodule module top; child u(),v(); endmodule\n')
    run([compiler, empty, '--emit-ir', output/'empty.json', '-o', output/'empty'])
    assert run([output/'empty']).stdout == ''
    empty_ir=json.loads((output/'empty.json').read_text())
    assert len(empty_ir['scopes']) == 3 and empty_ir['signal_count'] == 0
    clobber=run([compiler, empty, '--emit-ir', empty, '--emit-only'], ok=False)
    assert clobber.returncode != 0 and 'overwrite an input' in clobber.stdout
    print('PASS empty hierarchy and IR path protection')
    loop_source = output / 'zero_loop.v'
    # Constant continuous delays are supported; retain the old rejected syntax
    # as an executed positive case with an independently known result.
    delayed_source=output/'delayed_assign.v'
    delayed_source.write_text('module top; wire a; assign #1 a=1; initial begin #2; $display("TRACE delayed a=%b",a); $finish; end endmodule\n')
    delayed=output/'delayed_assign'
    run([compiler,delayed_source,'-o',delayed])
    p=run([delayed]);assert p.stdout.splitlines()==['TRACE delayed a=1'],p.stdout
    print('PASS constant continuous assignment delay')
    loop_source.write_text('module top; reg q; always q=1; endmodule\n')
    loop = output / 'zero_loop'
    run([compiler, loop_source, '-o', loop])
    p = run([loop, '--max-events', '100'], ok=False)
    assert p.returncode == 1 and 'limit exceeded' in p.stdout, p.stdout
    print('PASS bounded zero-delay loop')
    feedback_source = output / 'feedback_loop.v'
    feedback_source.write_text("module top; wire a; assign a=(a===1'b0)?1'b1:1'b0; endmodule\n")
    feedback = output / 'feedback_loop'
    run([compiler, feedback_source, '-o', feedback])
    p = run([feedback, '--max-events', '100'], ok=False)
    assert p.returncode == 1 and 'limit exceeded' in p.stdout, p.stdout
    print('PASS bounded continuous feedback loop')
    part_loop_source = output/'partial_feedback.v'
    part_loop_source.write_text("module top; wire [7:0] a; assign a[0]=(a[0]===1'b0)?1'b1:1'b0; endmodule\n")
    run([compiler, part_loop_source, '-o', output/'partial_feedback'])
    p=run([output/'partial_feedback', '--max-events', '100'], ok=False)
    assert p.returncode == 1 and 'limit exceeded' in p.stdout, p.stdout
    print('PASS bounded partial-driver feedback loop')
    for kind, text in {
        'while': "while(1'b1) ;",
        'do_while': "do ; while(1'b1);",
        'for': "for(q=0;q<1;q=0) ;",
        'repeat': "repeat(64'hffffffffffffffff) ;",
        'forever': "forever ;",
    }.items():
        source=output/f'loop_{kind}.v'
        source.write_text(f'module top; reg q; initial {text} endmodule\n')
        native=output/f'loop_{kind}'
        run([compiler, source, '-o', native])
        p=run([native, '--max-events', '100'], ok=False)
        assert p.returncode==1 and 'limit exceeded' in p.stdout, p.stdout
        print(f'PASS bounded {kind} loop')
    (output / 'results.json').write_text(json.dumps(results, indent=2)+'\n')

if __name__ == '__main__':
    main()
