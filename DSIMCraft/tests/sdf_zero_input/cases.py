"""Observe zero-delay MIPD versus an unannotated receiver in the same VCS run.

The immediate reads intentionally use XMR; these vendor discriminators do not
claim that native RTL supports XMR or that eliminating MIPD is already safe.
"""
from pathlib import Path
import json
import sys

def make(out, control=False):
    revised = True
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    scale = '`timescale 1ps/1ps\n'
    cases = {}
    for name in (['ic-positive'] if control else ['ic-zero', 'port-zero', 'ic-increment-zero', 'ic-replace-zero',
                 'port-multi-zero', 'ic-zero-with-path', 'ic-zero-with-edge', 'ic-zero-with-check']):
        work = out / name; work.mkdir()
        multi = name == 'port-multi-zero'
        path = '(posedge A => (Z:A))=7;' if name == 'ic-zero-with-edge' else '(A=>Z)=' + ('7;' if name == 'ic-zero-with-path' else '0;')
        if name == 'ic-zero-with-check': path += '$width(posedge A,2);'
        (work / 'cells.v').write_text(scale + 'module CELL(input A,output Z);assign Z=A;specify ' + path + ' endspecify endmodule\n')
        (work / 'cells.lib').write_text('library(l){cell(CELL){pin(A){direction:input;}pin(Z){direction:output;function:"A";}}}\n')
        net = 'wire n;assign n=a;assign n=b;' if multi else 'wire n;assign n=a;'
        connection = 'n'
        if revised and not multi: net = ''; connection = 'a'
        (work / 'net.v').write_text(scale + 'module dut(input a,b,output z);' + net + 'CELL u0(.A(' + connection + '),.Z(z));endmodule\n')
        if name.startswith('port'):
            cell, instance, entries = 'CELL', 'u0', '(ABSOLUTE(PORT A (0)))'
        else:
            cell, instance = 'dut', ''
            entries = '(ABSOLUTE(INTERCONNECT a u0/A (0)))'
            if name == 'ic-positive': entries = '(ABSOLUTE(INTERCONNECT a u0/A (9)))'
            if name == 'ic-increment-zero': entries = '(ABSOLUTE(INTERCONNECT a u0/A (9)))(INCREMENT(INTERCONNECT a u0/A (-9)))'
            if name == 'ic-replace-zero': entries = '(ABSOLUTE(INTERCONNECT a u0/A (9))(INTERCONNECT a u0/A (0)))'
        (work / 'delay.sdf').write_text('(DELAYFILE(SDFVERSION "3.0")(DIVIDER /)(TIMESCALE 1ps)'
            f'(CELL(CELLTYPE "{cell}")(INSTANCE {instance})(DELAY{entries})))\n')
        observe = '$display("TRACE t=%0t d=%b e=%b",$time,d.u0.A,e.u0.A);'
        changes = "a=0;b=1'bz;" + observe + '#10;'
        for values in ["a=1;", "a=0;a=1;a=0;", "a=1;#0;a=0;", "a=1'bx;", "a=1'bz;", "a=0;b=1;", "b=1'bz;", "a=1;"]:
            changes += values + observe + '#10;'
        (work / 'tb.v').write_text(scale + 'module top;reg a,b;wire zd,ze;dut d(a,b,zd),e(a,b,ze);\n'
            'initial begin $sdf_annotate("delay.sdf",d,,"annotation.log","TYPICAL");$dumpfile("vcs.vcd");$dumpvars(0,top);end\n'
            'always @(d.u0.A or e.u0.A) begin ' + observe + 'end\n'
            'initial begin ' + changes + '#10;$finish;end endmodule\n')
        cases[name] = dict(multi_driver=multi, purpose='paired zero MIPD and unannotated input observation')
    (out / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    return cases
