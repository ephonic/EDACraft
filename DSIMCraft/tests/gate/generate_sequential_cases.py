#!/usr/bin/env python3
"""Independent scalar state/bit oracle and deterministic structural fixtures."""
import argparse,json,random
from itertools import product
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ALTERNATES={}

def logic(v): return 'x' if v in 'xz' else v
def inv(v): return {'0':'1','1':'0','x':'x','z':'x'}[v]
def merge(values): return values[0] if all(v==values[0] for v in values) else 'x'
def band(a,b): return '0' if '0' in (a,b) else '1' if a==b=='1' else 'x'
def bor(a,b): return '1' if '1' in (a,b) else '0' if a==b=='0' else 'x'
def options(v): return '01' if logic(v)=='x' else v

class Storage:
    def __init__(self,latch=False,negative=False,action='XX'):
        self.q=self.n='x'; self.previous=None; self.latch=latch;self.negative=negative;self.action=action
    def update(self,c,d,r='0',s='0'):
        c=inv(c) if self.negative else logic(c);d=logic(d);r=logic(r);s=logic(s)
        event=(c,r,s,d) if self.latch else (c,r,s)
        if self.previous==event:return
        old='x' if self.previous is None else self.previous[0]
        self.previous=event
        # Enumerate possible captures, then apply the attribute's truth table.
        captures=[False]
        if self.latch: captures=[False,True] if c=='x' else [c=='1']
        elif old=='0' and c=='1':captures=[True]
        elif (old=='0' and c=='x') or (old=='x' and c=='1'):captures=[False,True]
        candidates=[]
        def action(op,value): return {'L':'0','H':'1','N':value,'T':inv(value),'X':'x'}[op]
        for reset,set_,capture in product(options(r),options(s),captures):
            if reset==set_=='1': candidates.append((action(self.action[0],self.q),action(self.action[1],self.n)))
            elif reset=='1':candidates.append(('0','1'))
            elif set_=='1':candidates.append(('1','0'))
            else:candidates.append((d,inv(d)) if capture else (self.q,self.n))
        self.q=merge([x[0] for x in candidates]);self.n=merge([x[1] for x in candidates])
    def pair(self):return self.n+self.q

def fixture(name,net,decl,inst,steps,records):
    tb='\n'.join(['module top;',decl,inst,'initial begin',*steps,'$finish;','end endmodule'])+'\n'
    return name,net,tb,records

def edges(latch=False):
    name='seq_latches' if latch else 'seq_edges'; pin='G' if latch else 'C'; p='LATCH' if latch else 'DFF'
    net=f'''module dut(input c,d,output [3:0] y);
{p}P a(.{pin}(c),.D(d),.Q(y[0]),.QN(y[1]));
{p}N b(.{pin}(c),.D(d),.Q(y[2]),.QN(y[3]));
endmodule
'''
    states=[Storage(latch),Storage(latch,True)];steps=[];records=[];alternate=[];c=d='x'
    def step(nc,nd):
        nonlocal c,d
        c,d=nc,nd;steps.append(f"c=1'b{c}; d=1'b{d}; #1;")
        for s in states:s.update(c,d)
    for i,(seed,data,old,new) in enumerate(product('01x','01xz','01xz','01xz')):
        step('0',seed);step('1',seed);step('0',seed)
        step('0',data);step(old,data)
        before=states[1].pair()+states[0].pair()
        c=new;steps.append(f"c=1'b{c}; #0;")
        for s in states:s.update(c,d)
        y=states[1].pair()+states[0].pair()
        steps.append(f'$display("TRACE i=%0d phase=0 c=%b d=%b y=%b",{i},c,d,y);');steps.append('#1;')
        steps.append(f'$display("TRACE i=%0d phase=1 c=%b d=%b y=%b",{i},c,d,y);')
        records += [f'TRACE i={i} phase=0 c={c} d={d} y={before}',f'TRACE i={i} phase=1 c={c} d={d} y={y}']
        alternate += [f'TRACE i={i} phase=0 c={c} d={d} y={y}',f'TRACE i={i} phase=1 c={c} d={d} y={y}']
    ALTERNATES[name]=alternate
    return fixture(name,net,'reg c,d; wire [3:0] y;','dut u(c,d,y);',steps,records)

def asynchronous():
    net='''module dut(input c,d,r,s,output [11:0] y);
DFFR a(.C(c),.D(d),.R(r),.Q(y[0]),.QN(y[1]));
DFFS b(.C(c),.D(d),.S(s),.Q(y[2]),.QN(y[3]));
DFFSR f(.C(c),.D(d),.R(r),.S(s),.Q(y[4]),.QN(y[5]));
DFFTN t(.C(c),.D(d),.R(r),.S(s),.Q(y[6]),.QN(y[7]));
LATCHR l(.G(c),.D(d),.R(r),.Q(y[8]),.QN(y[9]));
SRLATCH z(.R(r),.S(s),.Q(y[10]),.QN(y[11]));
endmodule
'''
    states=[Storage(),Storage(),Storage(action='LL'),Storage(action='TN'),Storage(True),Storage(True,action='LH')]
    values={p:'x' for p in 'cdrs'};steps=[];records=[]
    def update(pin,value):
        values[pin]=value;steps.append(f"{pin}=1'b{value}; #1;")
        c,d,r,s=(values[p] for p in 'cdrs')
        for st,args in zip(states,[(c,d,r,'0'),(c,d,'0',s),(c,d,r,s),(c,d,r,s),(c,d,r,'0'),('0','0',r,s)]):st.update(*args)
    stimuli=list(product('01xz',repeat=4));random.Random(1017).shuffle(stimuli)
    stimuli += [('0','0','1','0'),('0','0','1','1'),('0','1','1','1'),('0','x','1','1'),('1','x','1','1')]
    for i,(c,d,r,s) in enumerate(stimuli):
        for pin,value in [('d',d),('r',r),('s',s),('c',c)]:update(pin,value)
        y=''.join(st.pair() for st in reversed(states))
        steps.append(f'$display("TRACE i=%0d c=%b d=%b r=%b s=%b y=%b",{i},c,d,r,s,y);')
        records.append(f'TRACE i={i} c={c} d={d} r={r} s={s} y={y}')
    return fixture('seq_async',net,'reg c,d,r,s; wire [11:0] y;','dut u(c,d,r,s,y);',steps,records)

def feedback():
    net='''module dut(input c,d,e,a,oe,output [5:0] y);
DFFE f(.C(c),.D(d),.E(e),.Q(y[0]),.QN(y[1]));
DFFOUT o(.C(c),.D(d),.A(a),.E(oe),.Q(y[2]),.QN(y[3]),.Y(y[4]),.TQ(y[5]));
endmodule
'''
    ff=Storage();out=Storage();steps=[];records=[];alternate=[]
    def step(c,d,e,a,oe,wait='#1'):
        steps.append(f"c=1'b{c}; d=1'b{d}; e=1'b{e}; a=1'b{a}; oe=1'b{oe}; {wait};")
        ff.update(c,bor(band(d,e),band(ff.q,inv(e))));out.update(c,d)
    for i,(seed,d,e,a,oe) in enumerate(product('01x','01xz','01xz','01xz','01xz')):
        step('0',seed,'1','0','0');step('1',seed,'1','0','0');step('0',seed,'1','0','0')
        step('0',d,e,a,oe)
        def result():
            tri=out.q if oe=='1' else 'z' if oe=='0' else 'x'
            return tri+band(out.q,a)+out.pair()+ff.pair()
        before=result();step('1',d,e,a,oe,'#0');after=result()
        records += [f'TRACE i={i} phase=0 d={d} e={e} a={a} oe={oe} y={before}',f'TRACE i={i} phase=1 d={d} e={e} a={a} oe={oe} y={after}']
        alternate += [f'TRACE i={i} phase=0 d={d} e={e} a={a} oe={oe} y={after}',f'TRACE i={i} phase=1 d={d} e={e} a={a} oe={oe} y={after}']
    ALTERNATES['seq_feedback']=alternate
    # Execute the same corpus with compact runtime loops, keeping the expected
    # sequence independently enumerated above rather than expanding the TB FSM.
    steps=['i=0;']
    for counter,target,count in [('is','seed',3),('id','td',4),('ie','te',4),('ia','ta',4),('io','toe',4)]:
        steps += [f"for({counter}=0; {counter}<32'd{count}; {counter}={counter}+32'd1) begin",f'case({counter})']
        steps += [f"32'd{k}: {target}=1'b{v};" for k,v in enumerate('01xz'[:count])]
        steps += ['endcase']
    steps += ["c=0; d=seed; e=1; a=0; oe=0; #1;",'c=1; #1;','c=0; #1;',
              'd=td; e=te; a=ta; oe=toe; #1;','c=1; #0;',
              '$display("TRACE i=%0d phase=0 d=%b e=%b a=%b oe=%b y=%b",i,d,e,a,oe,y);','#1;',
              '$display("TRACE i=%0d phase=1 d=%b e=%b a=%b oe=%b y=%b",i,d,e,a,oe,y);',"i=i+32'd1;",'end end end end end']
    return fixture('seq_feedback',net,'reg c,d,e,a,oe,seed,td,te,ta,toe; reg [31:0] is,id,ie,ia,io,i; wire [5:0] y;','dut u(c,d,e,a,oe,y);',steps,records)

def pipeline():
    net=['module dut(input c,d,r,output [15:0] q,output t);']
    for i in range(16):net.append(f'DFFP g{i}(.C(c),.D('+('d' if i==0 else f'q[{i-1}]')+f'),.Q(q[{i}]));')
    net+=['TFF tf(.C(c),.R(r),.Q(t));','endmodule']
    steps=["c=0; d=0; nd=1; r=1; #1;","r=0; #1;"];records=[];q='x'*16;n='x'*16;t='0'
    for i,d in enumerate('01xz100110011001xz011010'):
        nd=inv(d);steps += [f"d=1'b{d}; nd=1'b{nd}; #1;","c<=1'b1; #0;",f'$display("TRACE i=%0d phase=0 c=%b q=%b n=%b t=%b nt=%b",{i},c,q,n,t,nt);']
        records.append(f'TRACE i={i} phase=0 c=0 q={q} n={n} t={t} nt={t}')
        q=q[1:]+logic(d);n=n[1:]+logic(nd);t=inv(t)
        steps += ['#1;',f'$display("TRACE i=%0d phase=1 c=%b q=%b n=%b t=%b nt=%b",{i},c,q,n,t,nt);','c=0; #1;']
        records.append(f'TRACE i={i} phase=1 c=1 q={q} n={n} t={t} nt={t}')
    return fixture('seq_pipeline','\n'.join(net)+'\n','reg c,d,nd,r; wire [15:0] q,n; wire t,nt;','dut u(c,d,r,q,t); dut v(c,nd,r,n,nt);',steps,records)

def regions():
    net="""module dut(input c,d,a,oe,r,output [7:0] y);
DFFOUT f(.C(c),.D(d),.A(a),.E(oe),.Q(y[0]),.QN(y[1]),.Y(y[2]),.TQ(y[3]));
LATCHR l(.G(c),.D(d),.R(r),.Q(y[4]),.QN(y[5]));
DFFR z(.C(c),.D(d),.R(r),.Q(y[6]),.QN(y[7]));
endmodule
"""
    steps=["c=0;d=0;a=1;oe=1;r=1;#1;r=0;#1;d=1;#1;"]
    records=[];alternate=[]
    events=[
      ('clock_inactive','c=1;#0;', '1','1010xxxx','10101101'),
      ('clock_settled','#1;', '1','01011101',None),
      ('outputs_active','c=0;#1;a=0;oe=0;#0;', '0','0101z001',None),
      ('reset_inactive','#1;r=1;#0;', '0','0101z001',None),
      ('reset_settled','#1;', '0','1010z001',None),
      ('pulse_rise','r=0;#1;d=0;a=1;oe=1;#1;c=1;#0;', '1','10101101','10100010'),
      ('pulse_fall','c=0;#0;', '0','10101101','10100010'),
      ('pulse_settled','#1;', '0','10100010',None),
      ('nba_clock','d=1;#1;c<=1;#0;', '0','10100010',None),
      ('nba_settled','#1;', '1','01011101',None),
    ]
    for name,action,c,y,iv in events:
        steps += [action,f'$display("TRACE {name} c=%b y=%b",c,y);']
        records.append(f'TRACE {name} c={c} y={y}');alternate.append(f'TRACE {name} c={c} y={iv or y}')
    ALTERNATES['seq_regions']=alternate
    return fixture('seq_regions',net,'reg c,d,a,oe,r; wire [7:0] y;','dut u(c,d,a,oe,r,y);',steps,records)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');args=ap.parse_args()
    for name,net,tb,expected in [edges(),edges(True),asynchronous(),feedback(),pipeline(),regions()]:
        for suffix,text in [('.net.v',net),('.tb.v',tb),('.expected.json',json.dumps(expected,indent=2)+'\n')]:
            path=ROOT/(name+suffix)
            if args.check:assert path.read_text()==text,path
            else:path.write_text(text)
        if name in ALTERNATES:
            path=ROOT/(name+'.icarus.json');text=json.dumps(ALTERNATES[name],indent=2)+'\n'
            if args.check:assert path.read_text()==text,path
            else:path.write_text(text)
        print(name,len(expected))
if __name__=='__main__':main()
