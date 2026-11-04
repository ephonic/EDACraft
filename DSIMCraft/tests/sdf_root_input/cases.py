"""Distinguish root-input MIPD policy from external driver kind and internal fanin."""
from pathlib import Path
import json

SCALE = '`timescale 1ps/1ps\n'


def make(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    cases = {}
    configurations = [
        ('root-reg', 'reg', False, False, '(ABSOLUTE{E9}{E3})'),
        ('root-assign', 'assign', False, False, '(ABSOLUTE{E9}{E3})'),
        ('root-buffer', 'buffer', False, False, '(ABSOLUTE{E9}{E3})'),
        ('root-module', 'module', False, False, '(ABSOLUTE{E9}{E3})'),
        ('root-multi', 'multi', False, False, '(ABSOLUTE{E9}{E3})'),
        ('internal-reg', 'reg', True, False, '(ABSOLUTE{E9}{E3})'),
        ('root-increment', 'reg', False, False, '(ABSOLUTE{E3})(INCREMENT{E20})(ABSOLUTE{E4})'),
        ('internal-increment', 'reg', True, False, '(ABSOLUTE{E3})(INCREMENT{E20})(ABSOLUTE{E4})'),
        ('root-port', 'reg', False, True, '(ABSOLUTE{E9}{E3})'),
        ('root-module-port', 'module', False, True, '(ABSOLUTE{E9}{E3})'),
        ('root-three', 'reg', False, False, '(ABSOLUTE{E9}{ET})'),
        ('internal-three', 'reg', True, False, '(ABSOLUTE{E9}{ET})'),
    ]
    for name, driver, internal, port, template in configurations:
        work = out / name; work.mkdir(exist_ok=True)
        (work / 'cells.v').write_text(SCALE + 'module CELL(input A,output Z);assign Z=A;specify(A=>Z)=0;endspecify endmodule\n')
        (work / 'cells.lib').write_text('library(l){cell(CELL){pin(A){direction:input;}pin(Z){direction:output;function:"A";}}}\n')
        body = 'wire n;CELL src(.A(a),.Z(n));CELL u0(.A(n),.Z(z));' if internal else 'CELL u0(.A(a),.Z(z));'
        (work / 'net.v').write_text(SCALE + 'module dut(input a,b,output z);' + body + 'endmodule\n')
        endpoint = 'PORT u0/A' if port else 'INTERCONNECT ' + ('src/Z' if internal else 'a') + ' u0/A'
        values = {f'E{n}':'(' + endpoint + f' ({n}))' for n in [3,4,9,20]}
        values['ET'] = '(' + endpoint + ' (3)(12)(4))'
        sdf = '(DELAYFILE(SDFVERSION "3.0")(DIVIDER /)(TIMESCALE 1ps)(CELL(CELLTYPE "dut")(INSTANCE)(DELAY'
        (work / 'delay.sdf').write_text(sdf + template.format(**values) + ')))\n')
        if driver == 'reg':
            declarations = 'reg a,b;'; source = 'a'; initialize = ''
        else:
            declarations = 'reg stimulus,b;wire a;'; source = 'stimulus'; initialize = ''
            if driver == 'assign': declarations += 'assign a=stimulus;'
            elif driver == 'buffer': declarations += 'buf(a,stimulus);'
            elif driver == 'module': declarations += 'EXT x(.I(stimulus),.O(a));'
            else:
                declarations += 'reg other;assign a=stimulus;assign a=other;'
                initialize = "other=1'bz;"
        steps = initialize + "b=1'bz;" + source + '=0;#40;'
        for value in ['1', "1'bz", "1'bx", '0']:
            steps += source + '=' + value + ';#40;'
        steps += source + '=1;#2;' + source + '=0;#40;' + source + '=1;#0;' + source + '=0;#40;'
        if driver == 'multi': steps += "other=1;#40;other=1'bz;#40;"
        tb = SCALE + 'module top;' + declarations + 'wire z;dut d(a,b,z);\n'
        tb += '`ifdef VCS_REFERENCE\ninitial begin $sdf_annotate("delay.sdf",d,,"annotation.log","TYPICAL");$dumpfile("vcs.vcd");$dumpvars(0,top);end\n'
        tb += 'always @(d.u0.A) $display("OBS t=%0t A=%b",$time,d.u0.A);\n`endif\n'
        tb += 'always @(z) $display("TRACE t=%0t z=%b",$time,z);\ninitial begin ' + steps + '#40;$finish;end endmodule\n'
        if driver == 'module': tb += 'module EXT(input I,output O);assign O=I;endmodule\n'
        (work / 'tb.v').write_text(tb)
        cases[name] = dict(driver=driver, internal_source=internal, port=port,
            collect_annotation_diagnostics=True,
            purpose='Separate root-port MIPD behavior from internal driver count and external RTL driver kind')
    (out / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    return cases


if __name__ == '__main__':
    import sys
    make(sys.argv[1])
