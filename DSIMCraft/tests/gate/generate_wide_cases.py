#!/usr/bin/env python3
"""Structural bus fixtures with independent bit-string truth/connection models."""
import argparse,json,random
from itertools import product
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def resolve(a,b):
    return ''.join(y if x=='z' else x if y=='z' or x==y else 'x' for x,y in zip(a,b))
def inv(bit): return {'0':'1','1':'0','x':'x','z':'x'}[bit]
def hex_bits(text): return ''.join(c*4 if c in 'xz' else f'{int(c,16):04b}' for c in text.replace('_',''))
def tb(name,decl,instance,stimuli,observe):
    return '\n'.join(['module top;',decl,instance,'initial begin',*stimuli,observe,'$finish; end endmodule'])+'\n'

def fixtures():
    net='''module lane(input [12:9] x,output [5:2] y);
assign y={x[10:9],x[12:11]};
endmodule
module wrap(input [3:0] a,output [9:6] y);
lane u({a[0],a[3:1]},y);
endmodule
module dut(input [7:4] a,input [3:0] b,output [15:0] y);
tri [2:5] ascending; wire [31:0] wide; wire [3:0] h;
assign ascending={a[5:4],b[3:2]};
wrap w(.a({a[7:6],b[1:0]}),.y(h));
assign wide={2{{a,b}}};
assign y={ascending[2:5],h,wide[7:4],wide[27:24]};
endmodule
'''
    rng=random.Random(1017); lines=[]; expected=[]
    for i,aa in enumerate(product('01xz',repeat=4)):
        a=''.join(aa); b=''.join(rng.choice('01xz') for _ in range(4))
        v=a[:2]+b[2:]; x=v[-1]+v[:3]; h=x[2:]+x[:2]
        y=a[2:]+b[:2]+h+a+'0000'
        lines += [f"a=4'b{a}; b=4'b{b}; #1;",'$display("TRACE i=%0d a=%b b=%b y=%b",'+str(i)+',a,b,y);']
        expected.append(f'TRACE i={i} a={a} b={b} y={y}')
    yield 'wide_connections',net,tb('wide_connections','reg [7:4] a; reg [3:0] b; wire [15:0] y;','dut u(a,b,y);',lines,''),expected

    net='''module probe(input [5:2] i,output [8:5] o,output [3:0] seen);
assign o=i; assign seen=o;
endmodule
module link(inout [6:3] io,output [3:0] seen);
assign io=4'bz1z0; assign seen=io;
endmodule
module dut(input a,b,inout [3:0] bus,
output [3:0] direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,
output [5:0] wide,output tied);
probe d(.i({a,b}),.o(direct),.seen(rd));
probe c(.i({a,b}),.o({cat}),.seen(rc));
probe w(.i({a,b}),.o(wide),.seen(rw));
probe t(.i({1'b1,1'b0,a,b,a,b}),.o(trunc));
probe f(.i('1),.o(fill));
probe n(.i(1'b1),.o(narrow));
probe p(.i({a,b}),.o(),.seen(opened));
assign direct=4'b0011; assign cat=4'b0011; assign wide=6'b110011;
link l(.io({bus[0],bus[2:1],bus[3]}),.seen(ri));
wire \\g/__dsim_pin_Y ; assign \\g/__dsim_pin_Y =1'b1;
INV g(.A({a,b}),.Y(leaf));
INV r(.A(b),.Y({tied,tied}));
endmodule
'''
    decl='reg a,b; reg [3:0] ext; wire [3:0] bus,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf; wire [5:0] wide; wire tied; assign bus=ext;'
    instance='dut u(a,b,bus,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied);'
    lines=[]; expected=[]
    fields=['direct','cat','rd','rc','rw','trunc','fill','narrow','opened','ri','leaf','wide','tied','bus']
    for a,b in product('01xz',repeat=2):
        i='00'+a+b; joined=resolve(i,'0011'); bus=resolve('01zz',a+b+a+b)
        values=[joined,joined,joined,joined,joined,a+b+a+b,'1111','0001',i,bus[3]+bus[1:3]+bus[0], '000'+inv(b),'xx'+joined,resolve('0',inv(b)),bus]
        lines += [f"a=1'b{a}; b=1'b{b}; ext=4'b{a+b+a+b}; #1;",'$display("TRACE a=%b b=%b '+' '.join(f+'=%b' for f in fields)+'",a,b,'+','.join(fields)+');']
        expected.append(f'TRACE a={a} b={b} '+' '.join(f+'='+v for f,v in zip(fields,values)))
    yield 'wide_ports',net,tb('wide_ports',decl,instance,lines,''),expected

    net='''module empty(input [2:0] a,output [2:0] y); endmodule
module dut(output [63:0] h,d,signed_value,unsized_value,unsized_x,integer_wrap,based_wrap,unsigned_max,based_signed_wrap,based_decimal_wrap,output [31:0] pad,sample,
output [15:0] sized,output [7:0] fill,output [1:0] trunc,
output [11:0] padded,allz,output [39:0] number,output [2:0] floating);
wire [1023:0] wide;
assign h=64'h80ff_0001_xz0f_7a21;
assign d=64'd18446744073709551615;
assign signed_value=4'sb1010; assign unsized_value=4294967296; assign unsized_x='hx;
assign integer_wrap=2147483648; assign based_wrap='h100000000; assign unsigned_max='hffffffff;
assign based_signed_wrap='sd4294967296; assign based_decimal_wrap='d4294967296;
assign pad={8'hx,8'hz,8'b1,8'o7};
assign sized={1'b1,3'b101,12'd1025};
assign fill='x;
assign wide={32{32'hca_fe_xz01}};
assign sample={wide[1023:1016],wide[19:0],wide[31:28]};
assign trunc=4'b1xz0; assign padded=8'hz; assign allz='z; assign number=1;
empty u(.a(3'b101),.y(floating));
endmodule
'''
    values=[hex_bits('80ff0001xz0f7a21'),'1'*64,'x'*8+'z'*8+'00000001'+'00000111','1101'+f'{1025:012b}','x'*8,hex_bits('caexz01c'),'z0','0000'+'z'*8,'z'*12,'0'*39+'1','zzz']
    values += ['1'*60+'1010','0'*64,'x'*64,'1'*33+'0'*31,f'{4294967296:064b}','0'*32+'1'*32,'1'*32+'0'*32,f'{4294967296:064b}']
    names=['h','d','pad','sized','fill','sample','trunc','padded','allz','number','floating','signed_value','unsized_value','unsized_x','integer_wrap','based_wrap','unsigned_max','based_signed_wrap','based_decimal_wrap']
    decl='wire [63:0] h,d,signed_value,unsized_value,unsized_x,integer_wrap,based_wrap,unsigned_max,based_signed_wrap,based_decimal_wrap; wire [31:0] pad,sample; wire [15:0] sized; wire [7:0] fill; wire [1:0] trunc; wire [11:0] padded,allz; wire [39:0] number; wire [2:0] floating;'
    instance='dut u(h,d,signed_value,unsized_value,unsized_x,integer_wrap,based_wrap,unsigned_max,based_signed_wrap,based_decimal_wrap,pad,sample,sized,fill,trunc,padded,allz,number,floating);'
    observe='$display("TRACE '+' '.join(n+'=%b' for n in names)+'",'+','.join(names)+');'
    yield 'wide_constants',net,tb('wide_constants',decl,instance,['#1;'],observe),['TRACE '+' '.join(n+'='+v for n,v in zip(names,values))]

    net='''module back(input wire [7:4] i,output wire [3:0] seen);
assign i=4'bzz10; assign seen=i;
endmodule
module single(input wire [9:9] a,output wire y); assign y=a; endmodule
module asc(input [1:2] a,output [9:8] y); assign y=a; endmodule
module dut(input a,b,output [3:0] plain,cat,sp,sc,sw,
output [1:0] short_bus,ascending,output one,output [3:0] open);
assign plain={a,b,a,b}; assign cat={a,b,a,b}; assign short_bus={a,b};
back p(.i(plain),.seen(sp));
back c(.i({cat}),.seen(sc));
back w(.i(short_bus),.seen(sw));
back z(.i(),.seen(open));
single s(.a({a}),.y(one)); asc t(.a({a,b}),.y(ascending));
endmodule
'''
    names=['plain','cat','sp','sc','sw','short_bus','ascending','one','open']
    decl='reg a,b; wire [3:0] plain,cat,sp,sc,sw,open; wire [1:0] short_bus,ascending; wire one;'
    instance='dut u(a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);'
    lines=[]; expected=[]
    for a,b in product('01xz',repeat=2):
        joined=resolve(a+b+a+b,'zz10')
        values=[joined,joined,joined,joined,resolve('00'+a+b,'zz10'),resolve(a+b,'10'),a+b,a,'zz10']
        lines += [f"a=1'b{a}; b=1'b{b}; #1;",'$display("TRACE a=%b b=%b '+' '.join(n+'=%b' for n in names)+'",a,b,'+','.join(names)+');']
        expected.append(f'TRACE a={a} b={b} '+' '.join(n+'='+v for n,v in zip(names,values)))
    yield 'wide_inputs',net,tb('wide_inputs',decl,instance,lines,''),expected

    net='''module probe(input [3:0] d,output [3:0] y,seen);
assign y=d; assign seen=y;
endmodule
module dut(input [3:0] d,output [3:0] perm,ps,repeat_net,rs,
output [1:0] left,right,output [3:0] cross_seen);
assign perm=4'b1111; assign repeat_net=4'b1111;
assign left=2'b01; assign right=2'b10;
probe p(.d(d),.y({perm[0],perm[3:1]}),.seen(ps));
probe r(.d(d),.y({repeat_net[0],repeat_net[0],repeat_net[0],repeat_net[0]}),.seen(rs));
probe c(.d(d),.y({left,right}),.seen(cross_seen));
endmodule
'''
    names=['perm','ps','repeat_net','rs','left','right','cross_seen']
    decl='reg [3:0] d; wire [3:0] perm,ps,repeat_net,rs,cross_seen; wire [1:0] left,right;'
    instance='dut u(d,perm,ps,repeat_net,rs,left,right,cross_seen);'
    lines=[]; expected=[]
    for i,bits in enumerate(product('01xz',repeat=4)):
        d=''.join(bits); joint=resolve(d,'1111'); common='1'
        for bit in d: common=resolve(common,bit)
        cross=resolve(d,'0110')
        values=[joint[1:]+joint[0],joint,'111'+common,common*4,cross[:2],cross[2:],cross]
        lines += [f"d=4'b{d}; #1;",'$display("TRACE d=%b '+' '.join(n+'=%b' for n in names)+'",d,'+','.join(names)+');']
        expected.append(f'TRACE d={d} '+' '.join(n+'='+v for n,v in zip(names,values)))
    yield 'wide_aliases',net,tb('wide_aliases',decl,instance,lines,''),expected

    net='''module dut(input [1:0] a,output y);
assign {y,y}=a;
endmodule
'''
    source='''module top;
reg [1:0] a; reg ready; reg [7:0] changes; wire y; dut u(a,y);
always @(y) if(ready) changes=changes+8'd1;
initial begin ready=0; changes=0; a=2'b01; #1; ready=1;
'''
    expected=[]
    states=[('10','x',0),('00','0',1),('11','1',2),('xz','x',3),('zz','z',4),('x1','x',5)]
    for a,y,n in states:
        source+=f'a=2\'b{a}; #1; $display("TRACE a=%b y=%b changes=%0d",a,y,changes);\n'
        expected.append(f'TRACE a={a} y={y} changes={n}')
    source+='$finish; end endmodule\n'
    yield 'wide_atomic',net,source,expected

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true'); args=ap.parse_args()
    for case,net,testbench,expected in fixtures():
        for suffix,text in [('net.v',net),('tb.v',testbench),('expected.json',json.dumps(expected,indent=2)+'\n')]:
            p=ROOT/(case+'.'+suffix)
            if args.check: assert p.read_text()==text,p
            else: p.write_text(text)
    # Preserve the measured Icarus differences separately from VCS/native.
    all_cases={case:expected for case,net,testbench,expected in fixtures()}
    alternatives={}
    alternatives['wide_atomic']=[line.rsplit('=',1)[0]+'='+str(int(line.rsplit('=',1)[1])+1) for line in all_cases['wide_atomic']]
    alternatives['wide_constants']=[' '.join(('unsized_value='+f'{4294967296:064b}' if part.startswith('unsized_value=') else 'integer_wrap='+f'{2147483648:064b}' if part.startswith('integer_wrap=') else 'based_signed_wrap='+f'{4294967296:064b}' if part.startswith('based_signed_wrap=') else part) for part in all_cases['wide_constants'][0].split())]
    alternatives['wide_ports']=[]
    alternatives['wide_inputs']=[]
    alternatives['wide_aliases']=[]
    for line in all_cases['wide_aliases']:
        d=line.split()[1].split('=')[1]
        parts=[p.split('=')[0]+'='+d if p.startswith(('ps=','rs=','cross_seen=')) else p for p in line.split()]
        alternatives['wide_aliases'].append(' '.join(parts))
    for row,(a,b) in enumerate(product('01xz',repeat=2)):
        line=all_cases['wide_ports'][row]
        parts=line.split(); parts=[('rc=00'+a+b if p.startswith('rc=') else 'rw=00'+a+b if p.startswith('rw=') else p) for p in parts]
        alternatives['wide_ports'].append(' '.join(parts))
        line=all_cases['wide_inputs'][row]
        parts=[('sw=zz'+resolve(a+b,'10') if p.startswith('sw=') else p) for p in line.split()]
        alternatives['wide_inputs'].append(' '.join(parts))
    for case,expected in alternatives.items():
        p=ROOT/(case+'.icarus.json'); text=json.dumps(expected,indent=2)+'\n'
        if args.check: assert p.read_text()==text,p
        else: p.write_text(text)
    print('PASS structural bus fixture generation')
if __name__=='__main__': main()
