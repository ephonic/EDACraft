"""Module identity/wildcard cases; vendor inputs are checked by SHA256."""
from pathlib import Path
import json


def make(output):
    out = Path(output); out.mkdir(parents=True, exist_ok=False)
    scale = '`timescale 1ps/1ps\n'
    body = '(input A,output Z);assign Z=A;specify(A=>Z)=0;endspecify endmodule\n'
    variants = {
        'identical': (scale, body, 'A'),
        'comments': (scale, '(input A, output Z); /* ignored comment */ assign Z = A;\n specify (A => Z) = 0; endspecify endmodule\n', 'A'),
        'precision': ('`timescale 1ps/100fs\n', body, 'A'),
        'unit': ('`timescale 10ps/1ps\n', body, 'A'),
        'initial-path': (scale, body.replace('(A=>Z)=0', '(A=>Z)=2'), 'A'),
        'function': (scale, body.replace('assign Z=A', 'assign Z=~A'), '!A'),
        'edge': (scale, body.replace('(A=>Z)=0', '(posedge A => (Z:A))=0'), 'A'),
    }
    cases = {}
    for variant, (dscale, dbody, function) in variants.items():
        for family, entry in [('port', '(PORT A (7))'), ('device', '(DEVICE Z (7))'), ('iopath', '(IOPATH A Z (7))')]:
            name = variant + '-' + family; work = out / name; work.mkdir()
            (work / 'cells.v').write_text(scale + 'module S' + body + dscale + 'module D' + dbody)
            (work / 'cells.lib').write_text('library(l){' + ''.join('cell(' + kind + '){pin(A){direction:input;}pin(Z){direction:output;function:"' + fn + '";}}' for kind, fn in [('S', 'A'), ('D', function)]) + '}\n')
            (work / 'net.v').write_text(scale + 'module dut(input a,output x,y);wire n;S src(.A(a),.Z(n));D fast(.A(n),.Z(x));D slow(.A(n),.Z(y));endmodule\n')
            (work / 'delay.sdf').write_text('(DELAYFILE(SDFVERSION "3.0")(TIMESCALE 1ps)(CELL(CELLTYPE "D")(INSTANCE *)(DELAY(ABSOLUTE' + entry + '))))\n')
            (work / 'tb.v').write_text(scale + 'module top;reg a;wire x,y;dut d(a,x,y);\n'
                '`ifdef VCS_REFERENCE\ninitial begin $sdf_annotate("delay.sdf",d,,"annotation.log","TYPICAL");$dumpfile("vcs.vcd");$dumpvars(0,top);end\n`endif\n'
                'always @(a or x or y) $display("TRACE t=%0t a=%b x=%b y=%b",$time,a,x,y);\n'
                "initial begin a=0;#100;a=1;#100;a=0;#100;a=1'bx;#100;a=1'bz;#100;a=1;#100;$finish;end endmodule\n")
            cases[name] = dict(variant=variant, family=family)
    (out / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    return cases


if __name__ == "__main__":
    import sys
    make(sys.argv[1])
