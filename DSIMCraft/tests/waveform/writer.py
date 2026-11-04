#!/usr/bin/env python3
"""Independent integers, sparse XORs, uint64 times and cross-language blocks."""
import json,random,subprocess,sys
from pathlib import Path
from reader import read,declarations,dwf
exe=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
widths=[1,7,8,9,31,32,63,64];state=[((1<<w)-1,(1<<w)-1) for w in widths]
expected=[(0,'time',None),(0,'control',['$dumpvars'])]
for i,v in enumerate(state):expected.append((0,'value',(i,v)))
expected.append((0,'control',['$end']))
commands=[];time=0;rng=random.Random(1017)
for step in range(4000):
    if step%13==0:
        time+=rng.randrange(4)
        commands.append('t '+str(time))
        if expected[-1][0]!=time:expected.append((time,'time',None))
    ident=rng.randrange(8);mask=(1<<widths[ident])-1
    if step%5==0:
        # High zeros in XOR planes should use trimmed delta encoding.
        a,b=state[ident];a^=1<<rng.randrange(widths[ident]);b^=rng.randrange(4)&mask
    elif step%5==1:
        a,b=rng.choice([(0,0),(mask,0),(mask,mask),(0,mask)])
    else:a,b=rng.getrandbits(widths[ident]),rng.getrandbits(widths[ident]) if step%2 else 0
    commands.append(f'v {ident} {a} {b}')
    if state[ident]!=(a,b):expected.append((time,'value',(ident,(a,b))))
    state[ident]=(a,b)
for n in [(1<<64)-2,(1<<64)-1]:
    commands.append('t '+str(n));expected.append((n,'time',None))
    a,b=state[7];a^=1;commands.append(f'v 7 {a} {b}');state[7]=(a,b);expected.append((n,'value',(7,(a,b))))
source='\n'.join(commands)+'\n';(out/'events.txt').write_text(source)
rows={}
for codec in ['raw','zstd']:
 for block in [1,17,16384]:
    dest=out/f'{codec}-{block}.dwf';dest.unlink(missing_ok=True)
    p=subprocess.run([exe,'--waveform',dest,'--wave-mode','ordered','--wave-codec',codec,'--wave-block-events',str(block)],input=source,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    (out/f'{codec}-{block}.log').write_text(p.stdout);assert p.returncode==0,p.stdout
    meta,events=read(dest);assert events==expected,(codec,block,len(events),len(expected))
    decl=declarations(meta);assert decl[('top','s7')][0]==decl[('top','escaped.scope','alias[63:0]')][0]
    with dest.open('rb') as f:
        r=dwf.Reader(f)
        for start,end in [(0,0),(4,7),((1<<64)-2,(1<<64)-1)]:
            baseline=[None]*8;selected=[]
            for t,k,payload in expected:
                if t<start and k=='value':baseline[payload[0]]=payload[1]
                if start<=t<=end:selected.append((t,k,payload))
            assert r.window(start,end)==(baseline,selected)
    rows[f'{codec}-{block}']={'status':'PASS','events':len(events),'bytes':dest.stat().st_size}
    print('PASS cross-language native writer independent oracle',codec,block,flush=True)
(out/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
