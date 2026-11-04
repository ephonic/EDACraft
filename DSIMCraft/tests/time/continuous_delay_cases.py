"""Independent, race-free expectations for continuous and primitive delays."""
CASES={
'scalar': ('''`timescale 1ns/1ps
module top;
 reg a=0;wire q1,q2;wire #(2,5,3) q3=a;
 assign #4 q1=a;assign #(2,5) q2=a;
 initial begin
  #0.001;$display("TRACE init q=%b%b%b",q1,q2,q3);
  #5;$display("TRACE zero q=%b%b%b",q1,q2,q3);a=1;
  #1;a=0;#5;$display("TRACE short q=%b%b%b",q1,q2,q3);
  a=1;#2.001;$display("TRACE rise q=%b%b%b",q1,q2,q3);
  #2;$display("TRACE all q=%b%b%b",q1,q2,q3);a=1'bx;
  #2.001;$display("TRACE x q=%b%b%b",q1,q2,q3);
  #2;a=1'bz;#2.001;$display("TRACE off2 q=%b%b%b",q1,q2,q3);
  #1;$display("TRACE off3 q=%b%b%b",q1,q2,q3);
  #1;$display("TRACE off4 q=%b%b%b",q1,q2,q3);$finish;
 end
endmodule
''',['TRACE init q=xxx','TRACE zero q=000','TRACE short q=000',
    'TRACE rise q=011','TRACE all q=111','TRACE x q=1xx',
    'TRACE off2 q=xzx',
    'TRACE off3 q=xzz','TRACE off4 q=zzz']),
'vector': ('''`timescale 1ns/1ps
module top;
 reg [3:0] a=0;wire [3:0] q;
 reg x=0;wire scalar;wire [0:0] bitvec;
 assign #(2,5,3) q=a;
 assign #(2,5,3) scalar=x;assign #(2,5,3) bitvec=x;
 initial begin
  #5.001;$display("TRACE init q=%b",q);a=1;
  #2.001;$display("TRACE rise q=%b",q);a=2;
  #2.001;$display("TRACE nonzero q=%b",q);
  a=4'b0x00;x=1'bx;#2.001;$display("TRACE unknown q=%b s=%b p=%b",q,scalar,bitvec);
  a=4'bzzzz;x=1'bz;#3.001;$display("TRACE z q=%b s=%b p=%b",q,scalar,bitvec);
  a=0;x=0;#4.999;$display("TRACE before q=%b s=%b p=%b",q,scalar,bitvec);
  #0.002;$display("TRACE fall q=%b s=%b p=%b",q,scalar,bitvec);$finish;
 end
endmodule
''',['TRACE init q=0000','TRACE rise q=0001','TRACE nonzero q=0001',
    'TRACE unknown q=0001 s=x p=x','TRACE z q=zzzz s=z p=z',
    'TRACE before q=zzzz s=z p=z','TRACE fall q=0000 s=0 p=0']),
'packed': ('''`timescale 1ns/1ps
module top;
 reg a=0;wire s;wire [0:0] v,b,p,c;
 assign #(5,2,3) s=a;assign #(5,2,3) v=a;
 assign #(5,2,3) b[0]=a;assign #(5,2,3) p[0:0]=a;assign #(5,2,3) {c}=a;
 initial begin
  #2.001;$display("TRACE initial q=%b%b%b%b%b",s,v,b,p,c);a=1'bx;
  #2.001;$display("TRACE scalar-x q=%b%b%b%b%b",s,v,b,p,c);
  #3;$display("TRACE vector-x q=%b%b%b%b%b",s,v,b,p,c);a=1'bz;
  #3.001;$display("TRACE off q=%b%b%b%b%b",s,v,b,p,c);$finish;
 end
endmodule
''',['TRACE initial q=00000','TRACE scalar-x q=xxxxx','TRACE vector-x q=xxxxx','TRACE off q=zzzzz']),
'parts': ('''`timescale 1ns/1ps
module top;
 reg [7:0] a=8'h12;wire [11:4] q;wire [3:0] hi,lo;wire dup;
 reg [256:0] wide={1'b1,256'h123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0};
 wire [256:0] copy;
 assign #3 {q[11:8],q[7:4]}=a;
 assign #3 {hi,lo}=a;assign #3 {dup,dup}=a[1:0];assign #3 copy=wide;
 initial begin
  #3.001;$display("TRACE first q=%h h=%h l=%h d=%b w=%h",q,hi,lo,dup,copy);
  a=8'ha5;wide={1'bx,256'b0};#1;a=8'h12;wide=0;
  #2.001;$display("TRACE cancel q=%h w=%h",q,copy);
  #1;$display("TRACE next q=%h h=%h l=%h d=%b w=%h",q,hi,lo,dup,copy);$finish;
 end
endmodule
''',['TRACE first q=12 h=1 l=2 d=x w=1123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0',
    'TRACE cancel q=12 w=1123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0',
    'TRACE next q=12 h=1 l=2 d=x w='+'0'*65]),
'drivers': ('''`timescale 1ns/1ps
module pass(inout p,output seen);assign seen=p;endmodule
module top;
 reg a=0,b=1;wire bus,seen;pass p(bus,seen);
 assign #3 bus=a;assign #5 bus=b;
 initial begin
  #5.001;$display("TRACE conflict b=%b s=%b",bus,seen);
  a=1;#1;a=0;#3.001;$display("TRACE canceled b=%b s=%b",bus,seen);
  b=1'bz;#5.001;$display("TRACE own b=%b s=%b",bus,seen);
  a=1;#3.001;$display("TRACE one b=%b s=%b",bus,seen);$finish;
 end
endmodule
''',['TRACE conflict b=x s=x','TRACE canceled b=x s=x','TRACE own b=0 s=0','TRACE one b=1 s=1']),
'precision': ('''`timescale 10ns/1ns
module coarse(output q);
 parameter R=1;
 reg a=0;assign #(0.15,0.25) q=a;
 initial begin #0.5;a=1;#R;a=0;end
endmodule
`timescale 1ns/1ps
module top;
 wire q;coarse c(q);
 initial begin
  #2.999;$display("TRACE before q=%b",q);
  #0.002;$display("TRACE initial q=%b",q);
  #3.998;$display("TRACE rise-before q=%b",q);
  #0.002;$display("TRACE rise q=%b",q);
  #10.998;$display("TRACE fall-before q=%b",q);
  #0.002;$display("TRACE fall q=%b",q);$finish;
 end
endmodule
''',['TRACE before q=x','TRACE initial q=0','TRACE rise-before q=0','TRACE rise q=1','TRACE fall-before q=1','TRACE fall q=0']),
'nba': ('''`timescale 1ns/1ps
module top;
 reg a=0;wire q,n;assign #3 q=a;not #1 inv(n,q);
 initial begin
  #4.001;$display("TRACE initial a=%b q=%b n=%b",a,q,n);
  a<=#2 1;#2.001;$display("TRACE nba a=%b q=%b n=%b",a,q,n);
  #3;$display("TRACE cont a=%b q=%b n=%b",a,q,n);
  #1;$display("TRACE gate a=%b q=%b n=%b",a,q,n);$finish;
 end
endmodule
''',['TRACE initial a=0 q=0 n=1','TRACE nba a=1 q=0 n=1','TRACE cont a=1 q=1 n=1','TRACE gate a=1 q=1 n=0']),
'dedup': ('''`timescale 1ns/1ps
module top;
 reg a=0,b=0;wire q;assign #5 q=(a|b);
 initial begin
  #5.001;a=1;#1;b=1;#3.999;$display("TRACE before q=%b",q);
  #0.002;$display("TRACE not-postponed q=%b",q);$finish;
 end
endmodule
''',['TRACE before q=0','TRACE not-postponed q=1']),
'finish': ('''`timescale 1ns/1ps
module top;reg a=0;wire q;assign #100 q=a;
 initial begin #1;$display("TRACE finish q=%b",q);$finish;end
endmodule
''',['TRACE finish q=x']),
}
# All 4-state data/enable pairs, without timing races. This small Python
# truth table is independent of the generated mux/boolean expression code.
values=['0','1','x','z'];lines=['`timescale 1ns/1ps','module top;reg a=0,e=0;wire b0,b1,n0,n1;']
for kind,name in [('bufif0','b0'),('bufif1','b1'),('notif0','n0'),('notif1','n1')]:
    lines.append(kind+' #(2,4,3) '+name+'_inst('+name+',a,e);')
lines+=['initial begin'];expected=[]
for data in values:
    for enable in values:
        lines+=['a=1\'b'+data+';e=1\'b'+enable+';#5;',
                '$display("TRACE tri a=%b e=%b out=%b%b%b%b",a,e,b0,b1,n0,n1);']
        result=''
        for low,invert in [(True,False),(False,False),(True,True),(False,True)]:
            if enable in ['x','z']:out='x'
            elif (enable=='0')!=low:out='z'
            elif data in ['x','z']:out='x'
            else:out=str(1-int(data)) if invert else data
            result+=out
        expected.append('TRACE tri a='+data+' e='+enable+' out='+result)
lines+=['$finish;end endmodule']
CASES['tristate']=('\n'.join(lines)+'\n',expected)

lines=['`timescale 1ns/1ps','module top;reg a=0,b=0;wire aa,nn,oo,rr,xx,ee,bb,ii;']
for kind,name,inputs in [('and','aa','a,b'),('nand','nn','a,b'),('or','oo','a,b'),('nor','rr','a,b'),
                         ('xor','xx','a,b'),('xnor','ee','a,b'),('buf','bb','a'),('not','ii','a')]:
    lines.append(kind+' #(2,4) '+name+'_inst('+name+','+inputs+');')
lines+=['initial begin'];expected=[]
def invert(v):return str(1-int(v)) if v in ['0','1'] else 'x'
for a in values:
    for b in values:
        lines+=['a=1\'b'+a+';b=1\'b'+b+';#5;',
                '$display("TRACE logic a=%b b=%b out=%b%b%b%b%b%b%b%b",a,b,aa,nn,oo,rr,xx,ee,bb,ii);']
        ab='0' if '0' in [a,b] else '1' if [a,b]==['1','1'] else 'x'
        ob='1' if '1' in [a,b] else '0' if [a,b]==['0','0'] else 'x'
        xb=str(int(a)^int(b)) if a in ['0','1'] and b in ['0','1'] else 'x'
        buf=a if a in ['0','1'] else 'x'
        expected.append('TRACE logic a='+a+' b='+b+' out='+ab+invert(ab)+ob+invert(ob)+xb+invert(xb)+buf+invert(buf))
lines+=['$finish;end endmodule']
CASES['logic']=('\n'.join(lines)+'\n',expected)

# These explicit alternate expectations follow IEEE 1800-2017 10.3.3 rather
# than the default VCS W-2024.09 observations. They are not a VCS oracle.
IEEE_CASES={
 'vector':(CASES['vector'][0],[
    'TRACE init q=0000','TRACE rise q=0001','TRACE nonzero q=0010',
    'TRACE unknown q=0x00 s=x p=x','TRACE z q=zzzz s=z p=z',
    'TRACE before q=zzzz s=z p=z','TRACE fall q=0000 s=0 p=0']),
 'packed':(CASES['packed'][0],[
    'TRACE initial q=00000','TRACE scalar-x q=x0x00','TRACE vector-x q=xxxxx','TRACE off q=zzzzz']),
}

# Full settled transition matrix, independently observed in three VCS runs.
# Include declaration, whole, part-select and concatenation targets, unchanged
# bits and one-bit packed nets. Print 1ps after integer delay boundaries.
lines=['`timescale 1ns/1ps','module top;',
       'reg [3:0] a=0;reg s=0;',
       'wire [3:0] v,part,cat;wire [3:0] #(7,11,5) decl=a;',
       'wire ss;wire [0:0] pv,ps,pc;',
       'assign #(7,11,5) v=a;assign #(7,11,5) part[3:0]=a;assign #(7,11,5) {cat}=a;',
       'assign #(7,11,5) ss=s;assign #(7,11,5) pv=s;assign #(7,11,5) ps[0:0]=s;assign #(7,11,5) {pc}=s;',
       'initial begin']
expected=[];delay={'0':11,'1':7,'x':5,'z':5}
for i,old in enumerate(['0','1','x','z']):
    for j,new in enumerate(['0','1','x','z']):
        lines.append("s=1'b"+old+";#20.001;s=1'b"+new+";#0.001;")
        for tick in range(1,13):
            label=f'TRACE s {i} {j} {tick} q='
            lines.append('#1;$display("'+label+'%b%b%b%b",ss,pv,ps,pc);')
            expected.append(label+(old if tick<delay[new] else new)*4)
matrix_values=['0000','0001','0010','0011','0x00','00z0','zzzz','xxxx']
for i,old in enumerate(matrix_values):
    for j,new in enumerate(matrix_values):
        lines.append("a=4'b"+old+";#20.001;a=4'b"+new+";#0.001;")
        for tick in range(1,13):
            label=f'TRACE v {i} {j} {tick} q='
            lines.append('#1;$display("'+label+'%b d=%b p=%b c=%b",v,decl,part,cat);')
            value=old if tick<delay[new[-1]] else new
            expected.append(label+value+' d='+value+' p='+value+' c='+value)
lines+=['$finish;end','endmodule']
CASES['matrix']=('\n'.join(lines)+'\n',expected)
