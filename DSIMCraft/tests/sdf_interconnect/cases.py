"""Executable INTERCONNECT oracle inputs; independent of the native scheduler."""
from pathlib import Path
import json

SCALE = '`timescale 1ps/1ps\n'
TRANSITIONS = ['0', '1', "1'bz", "1'bx", '0', "1'bx", '1', "1'bx", "1'bz", '0', "1'bz", '1', '0']

def make(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True); cases = {}
    basic = 'a=0;#100;' + ''.join('a=' + v + ';#100;' for v in TRANSITIONS[1:])
    pulse = 'a=0;#100;' + ''.join(f'a=1;#{width};a=0;#100;' for width in [1, 4, 8, 12, 30])
    def add(name, steps, entries, source_coarse=False, destination_coarse=False, multi=False):
        w = out / name; w.mkdir(exist_ok=True)
        model = lambda name, coarse: ('`timescale 1ns/10ps\n' if coarse else SCALE) + 'module ' + name + '(input A,output Z);assign Z=A;specify(A=>Z)=0;endspecify endmodule\n'
        (w / 'cells.v').write_text(model('S', source_coarse) + model('D', destination_coarse))
        (w / 'cells.lib').write_text('library(l){' + ''.join('cell(' + name + '){pin(A){direction:input;}pin(Z){direction:output;function:"A";}}' for name in ['S', 'D']) + '}\n')
        net = SCALE + 'module dut(input a' + (',b' if multi else '') + ',output x,y);wire n;S src(.A(a),.Z(n));'
        if multi: net += 'S other(.A(b),.Z(n));'
        net += 'D fast(.A(n),.Z(x));D slow(.A(n),.Z(y));endmodule\n'
        (w / 'net.v').write_text(net)
        sdf = '(DELAYFILE(SDFVERSION "3.0")(DIVIDER /)(TIMESCALE 1ps)'
        sdf += '(CELL(CELLTYPE "dut")(INSTANCE)(DELAY' + entries + ')))\n'
        (w / 'delay.sdf').write_text(sdf)
        tb = SCALE + 'module top;reg a' + (',b' if multi else '') + ';wire x,y;dut d(a,' + ('b,' if multi else '') + 'x,y);\n'
        tb += '`ifdef VCS_REFERENCE\ninitial begin $sdf_annotate("delay.sdf",d,,"annotation.log","TYPICAL");$dumpfile("vcs.vcd");$dumpvars(0,top);end\n`endif\n'
        tb += 'always @(x or y or d.fast.A or d.slow.A) $display("TRACE t=%0t x=%b y=%b fast=%b slow=%b",$time,x,y,d.fast.A,d.slow.A);\n'
        tb += 'initial begin ' + steps + '#100;$finish;end endmodule\n'
        (w / 'tb.v').write_text(tb)
        cases[name] = dict(multi_driver=multi, source_precision_fs=10000 if source_coarse else 1000,
                           destination_precision_fs=10000 if destination_coarse else 1000,
                           pins=['top.x', 'top.y', 'top.d.src.Z', 'top.d.fast.A', 'top.d.slow.A'])
    add('fanout', basic, '(ABSOLUTE(INTERCONNECT src/Z fast/A (3)(4)(6))(INTERCONNECT src/Z slow/A (9)(11)(13)))')
    add('twelve', basic, '(ABSOLUTE(INTERCONNECT src/Z fast/A ' + ''.join('(' + str(v) + ')' for v in [7,11,13,17,19,23,29,31,37,41,43,47]) + '))')
    add('pulses', pulse, '(ABSOLUTE(INTERCONNECT src/Z fast/A (7)(19))(INTERCONNECT src/Z slow/A (11)(23)))')
    add('destination-precision', basic, '(ABSOLUTE(INTERCONNECT src/Z fast/A (4)(6))(INTERCONNECT src/Z slow/A (5)(15)))', destination_coarse=True)
    add('source-precision', basic, '(ABSOLUTE(INTERCONNECT src/Z fast/A (4)(6))(INTERCONNECT src/Z slow/A (5)(15)))', source_coarse=True)
    add('increment', basic, '(ABSOLUTE(INTERCONNECT src/Z fast/A (2)))(INCREMENT(INTERCONNECT src/Z fast/A (4)))(INCREMENT(INTERCONNECT src/Z fast/A (-9)))(INCREMENT(INTERCONNECT src/Z fast/A (6)))')
    add('input-and-output', basic, '(ABSOLUTE(INTERCONNECT a src/A (5))(INTERCONNECT src/Z fast/A (7))(INTERCONNECT src/Z slow/A (11)))')
    add('multi-driver', "a=0;b=1'bz;#100;a=1;#100;b=0;#100;a=1'bz;#100;b=1;#100;a=0;#100;b=1'bz;#100;", '(ABSOLUTE(INTERCONNECT src/Z fast/A (3))(INTERCONNECT other/Z fast/A (9))(INTERCONNECT src/Z slow/A (5))(INTERCONNECT other/Z slow/A (13)))', multi=True)
    (out / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    return cases

if __name__ == '__main__':
    import sys
    make(sys.argv[1])
