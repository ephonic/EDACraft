"""Deterministic multiword checks against Python integers and per-bit 4-state rules."""
from pathlib import Path
import json,random,subprocess,sys
rng=random.Random(101718)
rows=[];expected=[]
def bits(a,b,w):return ''.join('xz'[not (a>>i&1)] if b>>i&1 else str(a>>i&1) for i in range(w-1,-1,-1))
def integer(s):return int(s,2)
def truth(s):return '1' if '1' in s else 'x' if 'x' in s or 'z' in s else '0'
def add(op,a,b,w,aw=None,bw=None,offset=0):
    aw=aw or w;bw=bw or w;m=(1<<w)-1
    aa,ax=a;ba,bx=b
    sa,sb=bits(aa,ax,aw),bits(ba,bx,bw)
    x,y=sa.rjust(w,'0')[-w:],sb.rjust(w,'0')[-w:]
    if op in ['+','-','*','/','%']:
        if ax or bx or (op in ['/','%'] and ba==0):out='x'*w
        else:out=f'{({"+":lambda:aa+ba,"-":lambda:aa-ba,"*":lambda:aa*ba,"/":lambda:aa//ba,"%":lambda:aa%ba}[op]()&m):0{w}b}'
    elif op in ['<<','>>']:
        if bx:out='x'*w
        elif ba>=w:out='0'*w
        else:out=(x[ba:]+'0'*ba) if op=='<<' else ('0'*ba+x[:w-ba])
    elif op in ['&','|','^']:
        def bit(a,b):
            if op=='&':return '0' if '0' in [a,b] else '1' if a==b=='1' else 'x'
            if op=='|':return '1' if '1' in [a,b] else '0' if a==b=='0' else 'x'
            return str(int(a)^int(b)) if a in '01' and b in '01' else 'x'
        out=''.join(bit(a,b) for a,b in zip(x,y))
    elif op in ['==','!=','===','!==','<','>','<=','>=']:
        size=max(aw,bw);x,y=sa.rjust(size,'0'),sb.rjust(size,'0')
        if op in ['===','!==']:out=str(int((x==y) if op=='===' else (x!=y)))
        elif op in ['==','!=']:
            mismatch=any(a!=b and a in '01' and b in '01' for a,b in zip(x,y))
            out=str(int(op=='!=')) if mismatch else 'x' if ax or bx else str(int(op=='=='))
        elif ax or bx:out='x'
        else:out=str(int({'<':aa<ba,'>':aa>ba,'<=':aa<=ba,'>=':aa>=ba}[op]))
    elif op in ['&&','||']:
        a,b=truth(sa),truth(sb)
        out=('0' if '0' in [a,b] else 'x' if 'x' in [a,b] else '1') if op=='&&' else ('1' if '1' in [a,b] else 'x' if 'x' in [a,b] else '0')
    elif op=='not':out=''.join({'0':'1','1':'0','x':'x','z':'x'}[v] for v in sa)
    elif op=='neg':out='x'*aw if ax else f'{(-aa&((1<<aw)-1)):0{aw}b}'
    elif op=='redand':out='0' if '0' in sa else 'x' if ax else '1'
    elif op=='redor':out=truth(sa)
    elif op=='redxor':out='x' if ax else str(sa.count('1')%2)
    elif op=='mux':out=''.join(a if a==b and a in '01' else 'x' for a,b in zip(x,y))
    elif op=='concat':out=sa+sb
    elif op=='slice':out=sa[aw-offset-w:aw-offset] if 0<=offset<=aw-w else 'x'*w
    elif op=='replace':out=sa[:aw-offset-w]+y+(sa[aw-offset:] if offset else '')
    elif op=='size':out=x
    elif op=='resolve':out=''.join(b if a=='z' else a if b=='z' or a==b else 'x' for a,b in zip(x,y))
    elif op=='case':
        size=max(aw,bw);x,y=sa.rjust(size,'0'),sb.rjust(size,'0');wild='xz' if offset==2 else 'z' if offset==1 else ''
        out=str(int(all(a==b or a in wild or b in wild for a,b in zip(x,y))))
    else:raise AssertionError(op)
    decimal=str(integer(out)) if set(out)<=set('01') else 'x' if set(out)=={'x'} else 'z' if set(out)=={'z'} else 'X' if 'x' in out else 'Z'
    rows.append(f'{op} {aw} {bw} {w} {offset} {aa:x} {ax:x} {ba:x} {bx:x}')
    expected.append(out+' '+decimal)
for w in [1,31,63,64,65,66,127,128,129,191,255,256,257,511,512,513,1024]:
    mask=(1<<w)-1
    values=[(0,0),(mask,0),(1<<(w-1),0),(1,0),(mask,mask),(0,mask),(0,1<<(w-1)),(1<<(w-1),1<<(w-1))]
    values += [(rng.getrandbits(w),0) for _ in range(8)]
    values += [(rng.getrandbits(w),rng.getrandbits(w)) for _ in range(5)]
    for a in values:
        b=rng.choice(values)
        for op in ['+','-','*','/','%','&','|','^','==','!=','===','!==','<','>','<=','>=','&&','||','mux','resolve','not','neg','redand','redor','redxor']:
            add(op,a,b,w)
        for shift in [0,1,31,32,63,64,65,w-1,w,w+1]:
            for op in ['<<','>>']:add(op,a,(shift,0),w,bw=max(65,w))
        for shift in [-1,0,max(0,w-65),w-1]:add('slice',a,(0,0),65,aw=w,bw=1,offset=shift)
        for mode in range(3):add('case',a,b,w,offset=mode)
        for width in [1,64,65,128,257]:add('size',a,b,width,aw=w,bw=w)
        add('concat',a,b,w*2,aw=w,bw=w)
        if w>=65:
            for start in [0,w-65]:add('replace',a,b,65,aw=w,bw=w,offset=start)
    # Mixed widths / assignment context wider than either operand.
    for _ in range(12):
        aw=rng.choice([1,64,65,127,128,129,257]);bw=rng.choice([1,64,65,128,256])
        a=(rng.getrandbits(aw),0);b=(rng.getrandbits(bw),0)
        for op in ['+','-','*','/','%','==','<','===','&','mux','concat']:
            add(op,a,b,max(aw,bw, w),aw,bw)
exe=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
(out/'input.txt').write_text('\n'.join(rows)+'\n');(out/'expected.txt').write_text('\n'.join(expected)+'\n')
p=subprocess.run([str(exe)],input='\n'.join(rows)+'\n',capture_output=True,text=True,timeout=120)
(out/'actual.txt').write_text(p.stdout);(out/'stderr.log').write_text(p.stderr)
assert p.returncode==0,p.stderr
actual=p.stdout.splitlines();assert len(actual)==len(expected),(len(actual),len(expected))
for i,(a,b) in enumerate(zip(actual,expected)):
    assert a==b,(i,rows[i],a,b)
(out/'results.json').write_text(json.dumps(dict(status='PASS',operations=len(rows),widths='1..1024 with limb boundaries and mixed contexts'),indent=2)+'\n')
print('PASS independent integer/four-state multiword operations',len(rows))
