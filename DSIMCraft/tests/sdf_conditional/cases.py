"""Independent scalar condition truth/delay tables and race-free observations."""
from pathlib import Path
import json

def make(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);cases={}
    def add(name,paths,entries,delays,*,alias='',increments=''):
        work=out/name;work.mkdir(exist_ok=True)
        (work/'cells.v').write_text('`timescale 1ps/1ps\nmodule CELL(input A,E,F,output Z);'+alias+'assign Z=A;specify '+paths+' endspecify endmodule\n')
        (work/'cells.lib').write_text('library(test){cell(CELL){pin(A){direction:input;}pin(E){direction:input;}pin(F){direction:input;}pin(Z){direction:output;function:"A";}}}\n')
        (work/'net.v').write_text('module dut(input A,E,F,output Z,W);CELL u0(.A(A),.E(E),.F(F),.Z(Z));CELL u1(.A(A),.E(F),.F(E),.Z(W));endmodule\n')
        sdf='(DELAYFILE (SDFVERSION "3.0") (TIMESCALE 1ps)'
        for i in range(2):sdf+='(CELL (CELLTYPE "CELL") (INSTANCE u'+str(i)+') (DELAY (ABSOLUTE '+entries+')'+increments+'))'
        (work/'delay.sdf').write_text(sdf+')\n')
        steps='A=0;E=0;F=1;#100;$display("TRACE init z=%b w=%b",Z,W);'
        expected=['TRACE init z=0 w=0'];time=100;previous=0
        # Separate condition updates from source changes. Sample 1ps after all
        # distinct arrival boundaries, including immediate/no-enabled-path cases.
        states=[('0','1',0,1),('1','0',1,0),("1'bx","1'bz",2,3),("1'bz","1'bx",3,2)]
        for index,(e,f,ec,fc) in enumerate(states):
            value=1-previous;steps+=f'E={e};F={f};#10;A={value};';time+=10
            dz=delays(ec,fc,previous,value);dw=delays(fc,ec,previous,value)
            last=0
            for point in sorted({1,dz+1,dw+1}):
                steps+=f'#{point-last};$display("TRACE n={index} t=%0t z=%b w=%b",$time,Z,W);'
                expected.append(f'TRACE n={index} t={time+point} z={value if point>dz else previous} w={value if point>dw else previous}')
                last=point
            steps+='#50;';time+=last+50;previous=value
        steps+='$finish;'
        tb='`timescale 1ps/1ps\nmodule top;reg A,E,F;wire Z,W;dut d(A,E,F,Z,W);\n'
        tb+='`ifdef VCS_REFERENCE\ninitial begin $sdf_annotate("delay.sdf",d,,"annotation.log","TYPICAL");$dumpfile("vcs.vcd");$dumpvars(0,top);end\n`endif\n'
        tb+='initial begin '+steps+'end endmodule\n';(work/'tb.v').write_text(tb)
        cases[name]=dict(expected=expected)
    add('truth','if(E)(A=>Z)=0;ifnone(A=>Z)=0;',
        '(COND E (IOPATH A Z (7) (11)))(CONDELSE (IOPATH A Z (19) (23)))',
        lambda e,f,a,b:((7 if b else 11) if e!=0 else (19 if b else 23)))
    add('overlap','if(E)(A=>Z)=0;if(!E)(A=>Z)=0;ifnone(A=>Z)=0;',
        '(COND E (IOPATH A Z (7)))(COND !E (IOPATH A Z (13)))(CONDELSE (IOPATH A Z (19)))',
        lambda e,f,a,b:13 if e==0 else 7)
    add('case-equality',"if(E===1'b1)(A=>Z)=0;if(E===1'b0)(A=>Z)=0;ifnone(A=>Z)=0;",
        "(COND E===1'b1 (IOPATH A Z (7)))(COND E===1'b0 (IOPATH A Z (13)))(CONDELSE (IOPATH A Z (19)))",
        lambda e,f,a,b:7 if e==1 else 13 if e==0 else 19)
    add('alias',"if(!EN || F===1'b1)(A=>Z)=0;ifnone(A=>Z)=0;",
        "(COND !EN || F===1'b1 (IOPATH A Z (7)))(CONDELSE (IOPATH A Z (19)))",
        lambda e,f,a,b:19 if e==1 and f!=1 else 7,alias='wire EN;assign EN=E;')
    add('edge','if(E)(posedge A=>(Z:A))=0;ifnone(A=>Z)=0;',
        '(COND E (IOPATH (posedge A) Z (7)))(CONDELSE (IOPATH A Z (19)))',
        lambda e,f,a,b:19 if e==0 or not b else 7)
    add('increment','if(E)(A=>Z)=0;ifnone(A=>Z)=0;',
        '(COND E (IOPATH A Z (7)))(CONDELSE (IOPATH A Z (19)))',
        lambda e,f,a,b:9 if e!=0 else 19,
        increments='(INCREMENT (COND E (IOPATH A Z (2))))')
    add('output-state',"if(Z===1'b0)(A=>Z)=0;ifnone(A=>Z)=0;",
        "(COND Z===1'b0 (IOPATH A Z (7)))(CONDELSE (IOPATH A Z (19)))",
        lambda e,f,a,b:7 if a==0 else 19)
    add('no-ifnone',"if(E===1'b1)(A=>Z)=0;",
        "(COND E===1'b1 (IOPATH A Z (7)))",lambda e,f,a,b:7 if e==1 else 0)
    add('unconditional-tie','(A=>Z)=0;if(E)(A=>Z)=0;',
        '(IOPATH A Z (13))(COND E (IOPATH A Z (7)))',lambda e,f,a,b:13 if e==0 else 7)
    (out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n');return cases

if __name__=='__main__':
    import sys
    make(sys.argv[1])
