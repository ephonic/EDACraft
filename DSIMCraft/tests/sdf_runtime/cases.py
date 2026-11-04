"""Independent Verilog functions/specify models and structural/native inputs."""
from pathlib import Path
import json
SCALE='`timescale 1ps/1ps\n'
def make(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    buf=('input A,output Z','assign Z=A;', [('A','Z')], 'pin(A){direction:input;}pin(Z){direction:output;function:"A";}')
    and2=('input A,B,output Z','assign Z=A&B;', [('A','Z'),('B','Z')], 'pin(A){direction:input;}pin(B){direction:input;}pin(Z){direction:output;function:"A&B";}')
    half=('input A,B,output Z,W','assign Z=A^B;assign W=A&B;', [('A','Z'),('B','Z'),('A','W'),('B','W')], 'pin(A){direction:input;}pin(B){direction:input;}pin(Z){direction:output;function:"A^B";}pin(W){direction:output;function:"A&B";}')
    ff=('input A,B,output Z','reg q;always @(posedge A)q<=B;assign Z=q;', [('posedge A','Z')], 'ff(IQ,IQN){clocked_on:"A";next_state:"B";}pin(A){direction:input;}pin(B){direction:input;}pin(Z){direction:output;function:"IQ";}')
    cases={}
    def add(name,model,steps,delays=None,path_text=None,sdf_text=None,instances=1):
        header,body,paths,lib=model;w=out/name;w.mkdir(exist_ok=True)
        delays=delays or [str(7+12*i) for i in range(len(paths))]
        specify=path_text or ''.join(f'({a} => ({z}:B))=0;' if a.startswith('posedge') else f'({a}=>{z})=0;' for a,z in paths)
        (w/'cells.v').write_text(SCALE+'module CELL('+header+');'+body+'specify '+specify+' endspecify endmodule\n')
        (w/'cells.lib').write_text('library(test){cell(CELL){'+lib+'}}\n')
        inputs='A,B' if 'input A,B' in header else 'A';outputs='Z,W' if ',W' in header else 'Z';ports=inputs+','+outputs
        nets=''.join(f'CELL u{i}(.A(A),'+('.B(B),' if 'B' in inputs else '')+f'.Z(Z)'+(', .W(W)' if 'W' in outputs else '')+');' for i in range(instances))
        (w/'net.v').write_text('module dut(input '+inputs+',output '+outputs+');'+nets+'endmodule\n')
        entries=''.join(f'(IOPATH {"("+a+")" if " " in a else a} {z} ({delay}))' for (a,z),delay in zip(paths,delays))
        sdf=sdf_text or '(DELAYFILE (SDFVERSION "3.0") (TIMESCALE 1ps)'+''.join(f'(CELL (CELLTYPE "CELL") (INSTANCE u{i}) (DELAY (ABSOLUTE {entries})))' for i in range(instances))+')\n'
        (w/'delay.sdf').write_text(sdf)
        tb=SCALE+'module top;reg '+inputs+';wire '+outputs+';dut d('+ports+');\n'
        tb+='`ifdef VCS_REFERENCE\ninitial begin $sdf_annotate("delay.sdf",d,,"annotation.log","TYPICAL");$dumpfile("vcs.vcd");$dumpvars(0,top);end\n`endif\n'
        tb+='always @('+outputs.replace(',', ' or ')+') $display("TRACE t=%0t z=%b'+(' w=%b' if 'W' in outputs else '')+'",$time,Z'+(',W' if 'W' in outputs else '')+');\n'
        tb+='initial begin '+steps+' #100;$finish;end endmodule\n'
        (w/'tb.v').write_text(tb);cases[name]={'outputs':outputs.split(','),'instances':instances}
    values=['0','1',"1'bz","1'bx",'0',"1'bx",'1',"1'bx","1'bz",'0',"1'bz",'1','0']
    add('twelve',buf,'A=0;#100;'+''.join('A='+v+';#100;' for v in values[1:]),['7) (11) (13) (17) (19) (23) (29) (31) (37) (41) (43) (47'])
    add('pulses',buf,"A=0;#100;A=1;#2;A=0;#100;A=1;#8;A=0;#100;A=1;#30;A=0;#100;A=1'bx;#3;A=0;",['7) (19'])
    add('latest',and2,'A=0;B=0;#100;A=1;#5;B=1;#100;A=0;#30;B=0;#100;B=1;#5;A=1;#100;A=0;B=0;#100;A=1;B=1;#100;A=0;B=0;#100;B=1;A=1;')
    add('delta-ties',and2,'A=0;B=0;#100;A=1;#0;B=1;#100;A=0;#0;B=0;#100;B=1;#0;A=1;')
    add('multiple',half,'A=0;B=0;#100;A=1;#100;B=1;#100;A=0;#100;B=0;')
    add('two-drivers',buf,'A=0;#100;A=1;#100;A=0;',instances=2)
    add('full',and2,'A=0;B=0;#100;A=1;#5;B=1;#100;A=0;B=0;#100;A=1;B=1;',path_text='(A,B *> Z)=0;')
    add('ff',ff,'A=0;B=0;#100;A=1;#100;A=0;B=1;#100;A=1;#100;A=0;#100;B=0;#2;A=1;')
    add('edge-filter',buf,"A=0;#100;A=1;#100;A=0;#100;A=1;",path_text="(posedge A => (Z:A))=0;")
    add('feedback',and2,'A=0;#100;A=1;#230;A=0;')
    w=out/'feedback'
    (w/'cells.v').write_text((w/'cells.v').read_text().replace('Z=A&B','Z=A&~B'))
    (w/'cells.lib').write_text((w/'cells.lib').read_text().replace('A&B',"A&B'"))
    (w/'net.v').write_text('module dut(input A,output Z); CELL u0(.A(A),.B(Z),.Z(Z)); endmodule\n')
    (w/'tb.v').write_text((w/'tb.v').read_text().replace('reg A,B','reg A').replace('dut d(A,B,Z)','dut d(A,Z)'))
    add('independent',buf,'A=0;B=1;#100;A=1;#5;B=0;#100;A=0;#5;B=1;')
    w=out/'independent'
    tb=(w/'tb.v').read_text().replace('reg A;wire Z;dut d(A,Z);','reg A,B;wire Z,W;dut d(A,Z);dut e(B,W);')
    tb=tb.replace('$dumpfile("vcs.vcd");','$sdf_annotate("delay.sdf",e,,"annotation-e.log","TYPICAL");$dumpfile("vcs.vcd");')
    tb=tb.replace('always @(Z) $display("TRACE t=%0t z=%b",$time,Z);','always @(Z or W) $display("TRACE t=%0t z=%b w=%b",$time,Z,W);')
    (w/'tb.v').write_text(tb);cases['independent']['outputs']=['Z','W']
    (out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n');return cases
if __name__=='__main__':
    import sys
    make(sys.argv[1])
