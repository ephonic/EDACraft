#!/usr/bin/env python3
"""Fixed, independent scalar truth model for gate functional fixtures."""
from itertools import product
from pathlib import Path
import argparse,json
ROOT=Path(__file__).resolve().parent

def band(a,b):
    return '0' if '0' in (a,b) else '1' if a==b=='1' else 'x'
def bxor(a,b):
    return str(int(a)^int(b)) if a in '01' and b in '01' else 'x'
def inv(a): return {'0':'1','1':'0','x':'x','z':'x'}[a]
def resolve(a,b): return b if a=='z' else a if b=='z' or a==b else 'x'
def tri(a,e): return a if e=='1' else 'z' if e=='0' else 'x'
def tri_icarus(a,e): return a if e=='1' else 'z' if e=='0' else 'z' if a=='z' else 'x'
def outputs(a,b,c):
    return 'zx'+band(a,b)+bxor(a,b)*2+band(a,bxor(b,c))+inv(a)+band(a,b)

def fixtures():
    lines=['module top;','reg [6:4] a; reg ext; wire [7:0] y,y2; wire bus,bus2;',
           'dut u(.a(a),.y(y),.bus(bus));',
           'dut v(.a({a[4],a[5],a[6]}),.y(y2),.bus(bus2));',
           'assign bus=ext;', 'initial begin']
    expected=[]
    for i,(a,b,c) in enumerate(product('01xz',repeat=3)):
        lines += [f"a=3'b{a+b+c}; ext=1'b{b}; #1;",
                  f'$display("TRACE i={i} y=%b y2=%b bus=%b bus2=%b",y,y2,bus,bus2);']
        expected.append(f'TRACE i={i} y={outputs(a,b,c)} y2={outputs(c,b,a)} bus={resolve(tri(a,c),b)} bus2={tri(c,a)}')
    lines+=['$finish; end endmodule']
    yield 'four_state','\n'.join(lines)+'\n',expected
    lines=['module top; reg a; wire y,c,f; dut u(a,y,c,f); initial begin']
    expected=[]
    for a in '01xz':
        lines += [f"a=1'b{a}; #1; $display(\"TRACE a=%b y=%b constant=%b floating=%b\",a,y,c,f);"]
        expected.append(f'TRACE a={a} y={inv(inv(a))} constant=1 floating=z')
    lines+=['$finish; end endmodule']
    yield 'hierarchy','\n'.join(lines)+'\n',expected

    lines=['module top; reg a,b; wire y,tied,missing,cx,cz; wire [0:0] one;',
           'dut u(a,b,y,tied,missing,cx,cz,one); initial begin']
    expected=[]
    for a,b in product('01xz',repeat=2):
        lines += [f"a=1'b{a}; b=1'b{b}; #1;",
                  '$display("TRACE a=%b b=%b y=%b tied=%b missing=%b cx=%b cz=%b one=%b",a,b,y,tied,missing,cx,cz,one);']
        expected.append(f'TRACE a={a} b={b} y={a} tied={resolve(bxor(a,b),band(a,b))} missing={band(a,"z")} cx=x cz=z one={inv(b)}')
    lines+=['$finish; end endmodule']
    yield 'connections','\n'.join(lines)+'\n',expected

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true'); args=ap.parse_args()
    for name,source,expected in fixtures():
        values={ROOT/(name+'.tb.v'):source,ROOT/(name+'.expected.json'):json.dumps(expected,indent=2)+'\n'}
        if name=='four_state':
            icarus=[]
            for i,(a,b,c) in enumerate(product('01xz',repeat=3)):
                icarus.append(f'TRACE i={i} y={outputs(a,b,c)} y2={outputs(c,b,a)} bus={resolve(tri_icarus(a,c),b)} bus2={tri_icarus(c,a)}')
            values[ROOT/(name+'.icarus.json')]=json.dumps(icarus,indent=2)+'\n'
        for path,text in values.items():
            if args.check: assert path.read_text()==text,path
            else: path.write_text(text)
    print('PASS gate fixture generation')
if __name__=='__main__': main()
