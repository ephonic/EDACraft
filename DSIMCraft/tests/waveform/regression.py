#!/usr/bin/env python3
"""Native waveform instrumentation, independent oracle, VCD/DWF and no-dump traces."""
import argparse,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from reader import ROOT,read,declarations,timeline,reference_timeline,dwf
from cases import CASES,EXPECTED


def run(command,cwd,log,ok=True):
    p=subprocess.run([str(x) for x in command],cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
    log.write_text(p.stdout)
    if ok:assert p.returncode==0,(command,p.stdout)
    else:assert p.returncode!=0,(command,p.stdout)
    return p.stdout


def traces(text):return [s for s in text.splitlines() if s.startswith('TRACE ')]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('compiler',type=Path);ap.add_argument('output',type=Path);ap.add_argument('--existing',action='store_true');a=ap.parse_args()
    compiler=a.compiler.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);report={}
    for name,source in CASES.items():
        w=out/name;w.mkdir(exist_ok=True);(w/'top.v').write_text(source)
        run([compiler,'--wave-support','top.v','-o',w/'simv'],w,w/'compile.log')
        assert traces(run([w/'simv'],w,w/'disabled.log'))==EXPECTED[name]
        for mode in ['settled','ordered']:
            outputs=[]
            for suffix,codec in [('vcd','zstd'),('dwf','zstd'),('raw.dwf','raw')]:
                dest=w/f'{mode}.{suffix}';dest.unlink(missing_ok=True)
                text=run([w/'simv','--waveform',dest,'--wave-format','vcd' if suffix=='vcd' else 'dwf','--wave-mode',mode,
                          '--wave-codec',codec,'--wave-block-events','3','--wave-timescale','10ps','--wave-stats'],w,w/f'{mode}.{suffix}.log')
                assert traces(text)==EXPECTED[name]
                meta,events=read(dest);outputs.append((meta,events))
                assert meta['header'][2]==['$timescale','10ps','$end']
                if suffix!='vcd':
                    with dest.open('rb') as f:
                        r=dwf.Reader(f);state,selection=r.window(1,1)
                        assert selection==[e for e in events if e[0]==1]
                        assert r.decoded_blocks<len(r.index)
            assert outputs[0]==outputs[1]==outputs[2],name
        settled_meta,settled=read(w/'settled.dwf');ordered_meta,ordered=read(w/'ordered.dwf')
        assert timeline(settled_meta,settled)==timeline(ordered_meta,ordered)
        decl=declarations(settled_meta)
        if name=='rtl_states':
            assert decl[('top','y')][0]==decl[('top','u','y')][0]
            assert decl[('top','q')][2]==['[15:8]']
            values=timeline(settled_meta,settled)
            assert values[('top','q')][2]==[(0,(0x12,0)),(1,(0x3c,0))]
            assert values[('top','d')][2]==[(0,(0,0)),(1,(0x5a,0)),(2,(0xa4,0x32)),(3,(0xff,0))]
            window=w/'selected.dwf';window.unlink(missing_ok=True)
            run([w/'simv','--waveform',window,'--wave-scope','top.u'],w,w/'selected.log')
            selected_meta,_=read(window);assert set(declarations(selected_meta))=={('top','u','a'),('top','u','y')}
            window=w/'depth.dwf';window.unlink(missing_ok=True)
            run([w/'simv','--waveform',window,'--wave-scope','top','--wave-depth','1'],w,w/'depth.log')
            selected_meta,_=read(window);assert set(declarations(selected_meta))=={('top',n) for n in ['clk','d','q','y']}
        if name=='ranges_escaped':
            assert decl[('top','one')][2]==['[5:5]'] and decl[('top','single')][2]==['[0:0]']
            assert ('top','name.with.dot') in decl
        if name=='quiet_finish':
            ident=decl[('top','a')][0]
            assert timeline(settled_meta,settled)[('top','a')][2]==[(0,(0,0))]
            assert [p[1] for t,k,p in ordered if t==1 and k=='value' and p[0]==ident]==[(1,0),(0,0)]
            assert max(t for t,k,p in settled)==5
        # Independent simulator compares settled traces; startup and #0 values are
        # compared as per-tick final values, not arbitrary Active ordering.
        dump='module capture;initial begin $dumpfile("reference.vcd");$dumpvars(0,top);end endmodule\n'
        (w/'dump.v').write_text(dump)
        run(['iverilog','-g2012','-s','top','-s','capture','-o','iv','top.v','dump.v'],w,w/'icarus-compile.log')
        (w/'reference.vcd').unlink(missing_ok=True)
        assert traces(run(['vvp','iv'],w,w/'icarus.log'))==EXPECTED[name]
        im,ie=read(w/'reference.vcd');assert reference_timeline(im,ie)==reference_timeline(settled_meta,settled),(name,timeline(im,ie),timeline(settled_meta,settled))
        # Runtime paths cannot clobber any existing file (including links).
        before=(w/'top.v').read_bytes()
        run([w/'simv','--waveform','top.v'],w,w/'clobber.log',False);assert (w/'top.v').read_bytes()==before
        for i,args in enumerate([['--wave-mode','bad'],['--waveform','x','--wave-format','bad'],['--waveform','x','--wave-mode','bad'],
                                ['--waveform','x','--wave-codec','bad'],['--waveform','x','--wave-block-events','0'],['--waveform','x','--wave-timescale','3ns'],
                                ['--waveform','x','--wave-scope','absent'],['--waveform'],['--unknown','x']]):
            run([w/'simv',*args],w,w/f'reject-{i}.log',False)
            assert not (w/'x').exists()
        report[name]={'status':'PASS','source_sha256':hashlib.sha256(source.encode()).hexdigest(),'trace':EXPECTED[name]}
        print('PASS native waveform',name,flush=True)
    if a.existing:
        # All previously verified gate cases retain the same trace while dumping
        # internal canonical Network nets, including multiple DUT instances.
        spec=importlib.util.spec_from_file_location('gate_regression',ROOT/'tests/gate/regression.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
        for name in g.CASES:
            w=out/('gate-'+name);w.mkdir(exist_ok=True)
            run(g.command(compiler,name)+['--wave-support','--emit-ir',w/'ir.json','-o',w/'simv'],w,w/'compile.log')
            expected=json.loads((ROOT/f'tests/gate/{name}.expected.json').read_text())
            assert traces(run([w/'simv'],w,w/'disabled.log'))==expected
            outputs=[]
            for suffix in ['vcd','dwf']:
                dest=w/f'internal.{suffix}';dest.unlink(missing_ok=True)
                assert traces(run([w/'simv','--waveform',dest,'--wave-format',suffix,'--wave-mode','ordered','--wave-block-events','127'],w,w/f'{suffix}.log'))==expected
                outputs.append(read(dest))
            assert outputs[0]==outputs[1],name
            ir=json.loads((w/'ir.json').read_text());decl=declarations(outputs[0][0])
            for scope in ir['gate_scopes']:
                parts=tuple(scope.split('.'));assert any(key[:-1]==parts for key in decl)
            report['gate-'+name]={'status':'PASS','trace':expected,'wave_declarations':len(decl),'events':len(outputs[0][1])}
            print('PASS native gate waveform',name,flush=True)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
