"""DEVICE/IOPATH interaction cases; controls test semantic alternatives."""
from pathlib import Path
import json

SCALE = '`timescale 1ps/1ps\n'

def make(out, followup=False):
    out = Path(out); out.mkdir(parents=True, exist_ok=True); cases = {}
    late = 'A=1;B=1;#100;A=0;#5;B=0;#100;A=1;#5;B=1;#100;A=0;#5;B=0;#100;'
    transitions = ['0', '1', "1'bz", "1'bx", '0', "1'bx", '1', "1'bx", "1'bz", '0', "1'bz", '1', '0']
    steady = 'A=0;B=1;#100;' + ''.join('A=' + v + ';#100;' for v in transitions[1:])

    def add(name, entries, initial='0', edge=False, steps=late):
        work = out / name; work.mkdir(exist_ok=False)
        specify = '(posedge A => (Z:A))=' + initial + ';' if edge else '(A=>Z)=' + initial + ';(B=>Z)=' + initial + ';'
        (work / 'cells.v').write_text(SCALE + 'module CELL(input A,B,output Z);assign Z=A&B;specify ' + specify + ' endspecify endmodule\n')
        (work / 'cells.lib').write_text('library(l){cell(CELL){pin(A){direction:input;}pin(B){direction:input;}pin(Z){direction:output;function:"A&B";}}}\n')
        (work / 'net.v').write_text('module dut(input A,B,output Z);CELL u0(.A(A),.B(B),.Z(Z));endmodule\n')
        (work / 'tb.v').write_text(SCALE + '''module top;reg A,B;wire Z;dut d(A,B,Z);
`ifdef VCS_REFERENCE
initial begin $sdf_annotate("delay.sdf",d,,"annotation.log","TYPICAL");$dumpfile("vcs.vcd");$dumpvars(0,top);end
`endif
always @(Z) $display("TRACE t=%0t z=%b",$time,Z);
initial begin ''' + steps + '$finish;end endmodule\n')
        (work / 'delay.sdf').write_text('(DELAYFILE(SDFVERSION "3.0")(TIMESCALE 1ps)(CELL(CELLTYPE "CELL")(INSTANCE u0)(DELAY' + entries + ')))\n')
        cases[name] = dict(edge=edge, initial=initial,
                          unchanged_cpp=not ('IOPATH' in entries and 'DEVICE' in entries))

    if followup:
        for name, entries, initial in [
            ('iopath-repeat', '(ABSOLUTE(IOPATH A Z (19))(IOPATH A Z (3)))', '0'),
            ('iopath-repeat-blocks', '(ABSOLUTE(IOPATH A Z (19)))(ABSOLUTE(IOPATH A Z (3)))', '0'),
            ('mixed-repeat-blocks', '(ABSOLUTE(IOPATH A Z (19)))(ABSOLUTE(DEVICE Z (7)))(ABSOLUTE(IOPATH A Z (3)))', '0'),
            ('mixed-device-repeat', '(ABSOLUTE(IOPATH A Z (19))(DEVICE Z (7))(DEVICE Z (3)))', '0'),
            ('device-first-iopath-repeat', '(ABSOLUTE(DEVICE Z (7))(IOPATH A Z (19))(IOPATH A Z (3)))', '0'),
            ('mixed-inc-then-absolute', '(ABSOLUTE(IOPATH A Z (19))(DEVICE Z (7)))(INCREMENT(DEVICE Z (-2)))(ABSOLUTE(DEVICE Z (3)))', '0'),
            ('initial31-increment', '(INCREMENT(DEVICE Z (2)))', '31'),
        ]:
            add(name, entries, initial=initial, steps=steady)
        (out / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
        return cases
    add('late-device', '(ABSOLUTE(IOPATH A Z (3))(IOPATH B Z (30))(DEVICE Z (19)))')
    add('late-static-max', '(ABSOLUTE(IOPATH A Z (19))(IOPATH B Z (30)))')
    add('late-device-first', '(ABSOLUTE(DEVICE Z (19))(IOPATH A Z (3))(IOPATH B Z (30)))')
    add('mixed-repeat', '(ABSOLUTE(IOPATH A Z (19))(DEVICE Z (7))(IOPATH A Z (3)))', steps=steady)
    add('mixed-decrement', '(ABSOLUTE(IOPATH A Z (19))(DEVICE Z (7)))(INCREMENT(DEVICE Z (-2)))', steps=steady)
    add('initial31-device7', '(ABSOLUTE(DEVICE Z (7)))', initial='31', steps=steady)
    add('initial7-device31', '(ABSOLUTE(DEVICE Z (31)))', initial='7', steps=steady)
    add('edge-mixed', '(ABSOLUTE(DEVICE Z (19))(IOPATH (posedge A) Z (3)))', edge=True, steps=steady)
    add('edge-static-max', '(ABSOLUTE(IOPATH (posedge A) Z (19)))', edge=True, steps=steady)
    add('four-state-mixed', '(ABSOLUTE(IOPATH A Z (7)(23)(11))(DEVICE Z (19)(3)(29)))', steps=steady)
    add('device-repeat', '(ABSOLUTE(DEVICE Z (9))(DEVICE Z (3)))', steps=steady)
    (out / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    return cases

if __name__ == '__main__':
    import sys
    make(sys.argv[1], '--followup' in sys.argv[2:])
