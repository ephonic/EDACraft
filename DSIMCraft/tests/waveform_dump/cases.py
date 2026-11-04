"""Distinguish dump selection, postponed snapshots and repeated control calls."""
from pathlib import Path
import hashlib
import json
import sys

def make(out):
    out.mkdir(exist_ok=False)
    common = '''`timescale 1ps/1ps
module leaf(input a,input [2:0] b,output [2:0] q);
  assign q={3{a}}^b;
endmodule
module wrap(input a,input [2:0] b,output [2:0] q);
  leaf inner(a,b,q);
endmodule
module top;
  reg a; reg [2:0] b; wire [2:0] q;
  wrap u(a,b,q);
  initial begin
    a=0;b=0;
    #2 a=1;b=5;
    #2 b=3'bx01;
    #2 a=0;b=3'bz10;
    #2 b=2;a=1;
    #2 b=7;
    #2 $finish;
  end
  initial begin
CONTROL
  end
endmodule
'''
    controls = {
        'all': '$dumpfile("vcs.vcd"); $dumpvars(0,top);',
        'late': '$dumpfile("vcs.vcd"); #5 $dumpvars(0,top);',
        'depth-one': '$dumpfile("vcs.vcd"); $dumpvars(1,top);',
        'depth-two': '$dumpfile("vcs.vcd"); $dumpvars(2,top);',
        'scope': '$dumpfile("vcs.vcd"); $dumpvars(0,top.u);',
        'signals': '$dumpfile("vcs.vcd"); $dumpvars(0,a,top.u.inner.q);',
        'same-time-more': '$dumpfile("vcs.vcd"); $dumpvars(0,a); $dumpvars(0,b);',
        'late-more': '$dumpfile("vcs.vcd"); $dumpvars(0,a); #5 $dumpvars(0,b);',
        'off-on-all': '$dumpfile("vcs.vcd"); $dumpvars(0,top); #3 $dumpoff; #3 $dumpon; #1 $dumpall; #1 $dumpoff; #1 $dumpon;',
        'same-time-off-on': '$dumpfile("vcs.vcd"); $dumpvars(0,top); #3 $dumpoff; $dumpon; $dumpoff; #3 $dumpon;',
        'before-first': '$dumpfile("vcs.vcd"); #1 $dumpall; #1 $dumpoff; #1 $dumpon; #1 $dumpvars(0,top);',
        'rename': '$dumpfile("vcs.vcd"); $dumpvars(0,top); #3 $dumpfile("second.vcd");',
        'file-only': '$dumpfile("vcs.vcd");',
        'default-file': '$dumpvars(0,top);',
        'no-arguments': '$dumpfile("vcs.vcd"); $dumpvars;',
        'depth-only': '$dumpfile("vcs.vcd"); $dumpvars(1);',
    }
    meta = {}
    for name, control in controls.items():
        work = out / name; work.mkdir()
        source = work / 'top.v'; source.write_text(common.replace('CONTROL', control))
        meta[name] = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), control=control)
    (out / 'cases.json').write_text(json.dumps(meta, indent=2) + '\n')
    return meta

if __name__ == '__main__': make(Path(sys.argv[1]).resolve())
