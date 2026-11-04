"""Full compiled flows crossing machine-word, port, NBA, driver and SDF boundaries."""
from pathlib import Path
import json,random
rng=random.Random(101718)
ROOT=Path(__file__).resolve().parents[2]

def make(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);cases=[]
    def write(name,files,expected=None,gate=False,sdf=False):
        w=out/name;w.mkdir()
        for file,text in files.items():(w/file).write_text(text)
        config=dict(name=name,sources=[str(w/'top.v')],vcs=dict(sources=[str(w/'top.v')]))
        if expected is not None:config['expected_trace']=expected
        if gate:
            config.update(gate_netlist=str(w/'net.v'),gate_top='dut',liberty=[str(ROOT/'tests/gate/cells.lib')])
            config['vcs']['sources'] += [str(w/'net.v'),str(w/'models.v')]
        if sdf:
            config.update(gate_models=[str(w/'models.v')],sdf=str(w/'delay.sdf'))
            config['vcs']['sdf_instance']='top.d'
        cases.append(config)
    declarations=[];assigns=[];steps=[];expected=[]
    for width in [65,127,128,129,256,257,512,1024]:
        tag=str(width);names=['add','sub','mul','div','mod','shl','shr']
        declarations += [f'reg [{width-1}:0] a{tag},b{tag};wire [{width-1}:0] '+','.join(n+tag for n in names)+';']
        assigns += [f'assign {n}{tag}=a{tag}{op}'+('65' if n in ['shl','shr'] else 'b'+tag)+';' for n,op in zip(names,['+','-','*','/','%','<<','>>'])]
        mask=(1<<width)-1
        for a,b in [(mask,1),(1<<(width-1),(1<<64)+1),(rng.getrandbits(width),rng.getrandbits(width))]:
            steps += [f"a{tag}={width}'h{a:x};b{tag}={width}'h{b:x};#100;",'$display("TRACE w='+tag+' '+' '.join(n+'=%h' for n in names)+' cmp=%b",'+','.join(n+tag for n in names)+f',a{tag}<b{tag});']
            vals=[(a+b)&mask,(a-b)&mask,a*b&mask,a//b,a%b,(a<<65)&mask,a>>65]
            expected.append('TRACE w='+tag+' '+' '.join(n+'='+f'{v:0{(width+3)//4}x}' for n,v in zip(names,vals))+' cmp='+str(int(a<b)))
    write('arithmetic',dict([('top.v','`timescale 1ps/1ps\nmodule top;\n'+'\n'.join(declarations+assigns)+ '\ninitial begin\n'+'\n'.join(steps)+'\n$finish;end endmodule\n')]),expected)
    # Across-word procedural slices / overlap, four-state ports and net resolution.
    source='''`timescale 1ps/1ps
module child(input [256:0] a,inout [256:0] bus,output [256:0] y);
assign bus={1'bz,a[255:0]};assign y=~a;endmodule
module top;reg [256:0] a,q,ext;wire [256:0] bus,y;assign bus=ext;child d(a,bus,y);
initial begin
a=257'h10000000000000000000000000000000000000000000000000000000000000001;q='0;ext='z;#100;
$display("TRACE a=%b bus=%b y=%b q=%b",a,bus,y,q);
q[130:63]=68'h123456789abcdef01;q[256:193]=64'hfedcba9876543210;#100;
$display("TRACE a=%b bus=%b y=%b q=%b",a,bus,y,q);
a='x;ext='0;{q[192:64],q[128:0]}<={129'h1ffffffffffffffffffffffffffffffff,129'h100000000000000000000000000000001};#100;
$display("TRACE a=%b bus=%b y=%b q=%b",a,bus,y,q);
a='z;ext='z;q='1;#100;
$display("TRACE a=%b bus=%b y=%b q=%b",a,bus,y,q);
a=257'h10000000000000000000000000000000000000000000000000000000000000000;ext='z;#100;
$display("TRACE hightruth=%b low=%b sized=%b",!!a,a[63:0],{64'h1,64'h0});
$finish;end endmodule
'''
    # VCS is the independent integration oracle; numeric.py covers per-bit rules.
    write('fourstate-ports',{'top.v':source})
    # Wide source/destination stub ports with 256 independent native gates.
    net='`timescale 1ps/1ps\nmodule dut(input [255:0] a,output [255:0] y);\n'+''.join(f'INV g{i}(.A(a[{i}]),.Y(y[{i}]));\n' for i in range(256))+'endmodule\n'
    model='`timescale 1ps/1ps\nmodule INV(input A,output Y);assign Y=~A;specify(A=>Y)=0;endspecify endmodule\n'
    steps=[];expected=[]
    for i,value in enumerate(['0','1','x','z','0']):
        steps += [f"a='{value};#100;",'$display("TRACE a=%b y=%b",a,y);']
        expected.append('TRACE a='+value*256+' y='+{'0':'1','1':'0','x':'x','z':'x'}[value]*256)
    tb='`timescale 1ps/1ps\nmodule top;reg [255:0] a;wire [255:0] y;dut d(a,y);initial begin\n'+'\n'.join(steps)+'\n$finish;end endmodule\n'
    # Models are functional-only in zero-delay VCS; do not feed specify bodies to RTL.
    write('gate-256',{'top.v':tb,'net.v':net,'models.v':model},expected,gate=True)
    inter=''.join(f'(INTERCONNECT a[{i}] g{i}/A ({3+i%4}))' for i in range(256))
    paths=''.join(f'(CELL (CELLTYPE "INV")(INSTANCE g{i})(DELAY(ABSOLUTE(IOPATH A Y (5)(7)))))' for i in range(256))
    sdf='(DELAYFILE(SDFVERSION "3.0")(DIVIDER /)(TIMESCALE 1ps)(CELL(CELLTYPE "dut")(INSTANCE)(DELAY(ABSOLUTE'+inter+')))'+paths+')\n'
    write('sdf-256',{'top.v':tb,'net.v':net,'models.v':model,'delay.sdf':sdf},expected,gate=True,sdf=True)
    # A wide intermediate with only narrow declarations must still select the wide backend.
    narrow='''module top;reg [63:0] a,b;reg [63:0] q;initial begin a=64'h1122334455667788;b=64'h8877665544332211;{a,b}=128'h123456789abcdef0fedcba9876543210;q={a,b};#1;$display("TRACE a=%h b=%h q=%h",a,b,q);$finish;end endmodule\n'''
    write('wide-intermediate',{'top.v':narrow},['TRACE a=123456789abcdef0 b=fedcba9876543210 q=fedcba9876543210'])
    (out/'manifest.json').write_text(json.dumps(dict(cases=cases),indent=2)+'\n')
    return out/'manifest.json'
if __name__=='__main__':
    import sys
    print(make(sys.argv[1]))
