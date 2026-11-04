"""Exercise the C910 frontend fixes, native semantics and rejection diagnostics."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
from cases import EXPECTED, make

compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();make(out)
report=dict(status='RUNNING',models={},rejections={})

def run(command,work,label,ok=True):
    command=list(map(str,command));start=time.monotonic()
    p=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=180)
    (work/(label+'.command.json')).write_text(json.dumps(command)+'\n')
    (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
    assert p.returncode>=0 and (p.returncode==0)==ok,(label,p.returncode,p.stdout,p.stderr[-3000:])
    return p,time.monotonic()-start

try:
    for name,expected in EXPECTED.items():
        work=out/name
        _,seconds=run([compiler,'--top','top',work/'tb.sv','--emit-cpp',work/'model.cpp','-o',work/'native'],work,'compile')
        p,_=run([work/'native'],work,'run')
        trace=[s for s in p.stdout.splitlines() if s.startswith('TRACE')]
        assert trace==expected,(name,trace,expected)
        report['models'][name]=dict(status='PASS',source_sha256=hashlib.sha256((work/'tb.sv').read_bytes()).hexdigest(),trace=trace,compile_seconds=round(seconds,3))
        print('PASS',name,flush=True)
    rejects={
        'real-cycle':('module top; top u(); endmodule\n',['cyclic module instantiation','top']),
        'bad-concat':('module top; initial $display("%b",{1,,2}); endmodule\n',['packed concatenation requires sized constant numbers']),
        'automatic-module':('module top; automatic integer v=3; endmodule\n',['syntax error']),
        'module-value':('module top; integer v; initial v=top; endmodule\n',['module definition is not a value']),
        'missing-member':('module top; initial $display("%d",top.no_such_member); endmodule\n',['unknown hierarchical member']),
    }
    for name,(source,wanted) in rejects.items():
        work=out/name;work.mkdir(exist_ok=True);(work/'tb.sv').write_text(source)
        protected=work/'model.cpp';protected.write_text('preserve existing output\n')
        p,_=run([compiler,'--top','top','--emit-only','--emit-cpp',protected,work/'tb.sv'],work,'reject',False)
        assert all(text in p.stderr for text in wanted),(name,p.stderr)
        assert protected.read_text()=='preserve existing output\n'
        report['rejections'][name]='PASS'
    work=out/'duplicate';work.mkdir(exist_ok=True)
    (work/'a.sv').write_text('module repeated; endmodule\n')
    (work/'b.sv').write_text('\nmodule repeated; endmodule\nmodule top; endmodule\n')
    p,_=run([compiler,'--emit-only','--top','top',work/'a.sv',work/'b.sv'],work,'reject',False)
    assert "duplicate module definition 'repeated'" in p.stderr and str(work/'a.sv')+':1:' in p.stderr and str(work/'b.sv')+':2:' in p.stderr,p.stderr
    report['rejections']['duplicate']='PASS';report['status']='PASS'
finally:
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
