"""Generate elaboration through native compilation, timing, hierarchy and replay."""
from pathlib import Path
import json, subprocess, sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read, declarations, timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
def run(args,work,label,ok=True):
    p=subprocess.run(list(map(str,args)),cwd=work,capture_output=True,text=True,timeout=180)
    (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
    assert (p.returncode==0)==ok,(label,p.returncode,p.stdout,p.stderr)
    return p.stdout
def streams(path):
    meta,events=read(path);values=[[] for _ in meta['signals']]
    for t,k,v in events:
        if k=='value':values[v[0]].append((t,v[1]))
    return {name:(w,r,values[i]) for name,(i,w,r) in declarations(meta).items()}
def packed(bits):
    return (int(''.join('1' if x in '1x' else '0' for x in bits),2),
            int(''.join('1' if x in 'xz' else '0' for x in bits),2))
def inverted(bits,mask):
    result=[]
    for i,x in enumerate(bits):
        result.append(('1' if x=='0' else '0' if x=='1' else 'x') if mask&(1<<(len(bits)-1-i)) else x)
    return ''.join(result)
expected={
 'design':['TRACE y=13223140 q=xxxxxxxx','TRACE q=13223140','TRACE y=fcecdccc q=fcecdccc'],
 'branches':['TRACE y=39 c6 9c b=9 9 9','TRACE y=xz0110z1 xx1001x0 xx1111x0 b=10z1'],
 'nested':[],
}
cache=(compiler.parent/'CMakeCache.txt').read_text().splitlines()
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache if '=' in x and not x.startswith('//')}
captures=0
for name,wanted in expected.items():
    work=out/name;work.mkdir(exist_ok=True);references={}
    for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
        run([compiler,ROOT/'tests/generate'/(name+'.sv'),'--wave-support',*flags,'--emit-cpp',work/(backend+'.cpp'),
             '--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-compile')
        trace=run([work/backend],work,backend+'-run')
        assert trace.splitlines()==wanted,(name,backend,trace)
        for mode in ['ordered','settled']:
            for fmt in ['vcd','dwf']:
                dest=work/(backend+'-'+mode+'.'+fmt);dest.unlink(missing_ok=True)
                assert run([work/backend,'--waveform',dest,'--wave-format',fmt,'--wave-mode',mode],work,backend+'-'+mode+'-'+fmt)==trace
                result=streams(dest);captures+=1
                if backend=='serial' and fmt=='vcd':references[mode]=result
                assert result==references[mode],(name,backend,mode,fmt)
        ir=json.loads((work/(backend+'.json')).read_text());scopes={s['path']:s for s in ir['scopes']}
        if name=='design':
            for i in range(4):
                assert f'top.u.lanes[{i}].active' in scopes
                assert f'top.u.lanes[{i}].inactive' not in scopes
                assert scopes[f'top.u.lanes[{i}].u']['parameters']['K']['bits']==f'{i:032b}'
            assert 'top.u.off' not in scopes and 'top.u.other' not in scopes and 'top.u.on' in scopes
        elif name=='branches':
            assert 'top.v.one' in scopes and 'top.v.genblk1.one' not in scopes
            assert all('no_iterations' not in s and 'unselected' not in s for s in scopes)
            assert all('top.'+u+'.genblk4' in scopes for u in ['u','v','w'])
        else:
            for unit in ['u','v']:
                for r in range(2):
                    for c in range(4):
                        params=scopes[f'top.{unit}.row[{r}].col[{c}]']['parameters']
                        assert params['POS']['bits']==f'{r*4+c:08b}'
            assert all('absent' not in s for s in scopes)
            lines=timeline(*read(work/(backend+'-settled.vcd')))
            for unit,input_name,output,wide,mask,times,bits in [
                ('u','a','x','wx',0x5a,[0,3,6],['00110101','11000111','x1z00110']),
                ('v','b','y','wy',0xa5,[0,4,8],['00010010','10101001','z0x11001'])]:
                assert lines[('top',output)][2]==[(t,packed(inverted(b,mask))) for t,b in zip(times,bits)]
                words=[b+'xxxx'+format(int('0123456789abcde',16),'060b') if unit=='u' else b*9 for b in bits]
                assert lines[('top',wide)][2]==[(t,packed(b)) for t,b in zip(times,words)]
            for unit in ['u','v']:
                for r in range(2):
                    assert lines[('top',unit,f'row[{r}]','ordinal')][2]==[(0,(r*4+1,0))]
            if backend=='parallel':
                run([work/backend,'--parallel-stats'],work,'stats')
                assert '"partitions":2' in (work/'stats.stderr').read_text()
    if name in ['design','nested']:
        code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
        code=code.replace('\ns.run();\n','''
s.run_until(1);
if(s.predict_until(16000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
''')
        (work/'replay.cpp').write_text(code)
        run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
        dest=work/'replay.dwf';dest.unlink(missing_ok=True)
        assert run([work/'replay','--waveform',dest,'--wave-mode','ordered'],work,'replay-run').splitlines()==wanted
        assert streams(dest)==references['ordered'];captures+=1
negative={
 'runtime-condition':'reg a;generate if(a)begin: bad wire q;end endgenerate',
 'runtime-bound':'reg a;genvar i;generate for(i=0;i<a;i=i+1)begin: bad wire q;end endgenerate',
 'nonconvergent':'genvar i;generate for(i=0;i<4;i=i)begin: bad wire q;end endgenerate',
 'active-unsupported':'generate if(1)begin: bad missing u();end endgenerate',
 'invalid-update':'generate for(genvar i=0;i<4;(i+1)++)begin: bad wire q;end endgenerate',
 'specialized-conflict':'logic clk;logic[1:0] q;generate for(genvar i=0;i<2;i=i+1)begin: g always_ff @(posedge clk)q[0]<=0;end endgenerate',
}
for name,body in negative.items():
    work=out/name;work.mkdir(exist_ok=True);source=work/'bad.sv';source.write_text('module top;\n'+body+'\nendmodule\n')
    run([compiler,source,'--emit-only','--emit-cpp',work/'bad.cpp'],work,'reject',False)
    assert 'dsim:' in (work/'reject.stderr').read_text()
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=3,captures=captures,negative_cases=len(negative),rollback_models=2),indent=2)+'\n')
print('PASS generate:',captures,'captures,',len(negative),'rejections, 2 rollback models')
