#!/usr/bin/env python3
"""Independent CLI summary, malformed input and source protection checks."""
import argparse,json,subprocess
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('compiler',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args()
    compiler=a.compiler.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    source=out/'test.sdf'
    raw=b'(DELAYFILE(SDFVERSION "3.0")(TIMESCALE 1ns)(CELL(CELLTYPE "BUF")(INSTANCE u)(DELAY(ABSOLUTE(IOPATH A Y (1:2:3))))))\n'
    source.write_bytes(raw)
    def run(args,valid=True):
        p=subprocess.run([str(compiler),*map(str,args)],capture_output=True,text=True,timeout=30)
        assert (p.returncode==0)==valid,(args,p.stdout,p.stderr)
        return p
    summary=out/'summary.json';p=run(['--sdf-check',source,'--emit-ir',summary]);data=json.loads(p.stdout)
    assert data==json.loads(summary.read_text())
    assert data['cells']==1 and data['entries']==1 and data['kinds']=={'IOPATH':1}
    assert data['annotation'] is False and data['timescale_fs']==1000000
    lists=out/'lists';lists.mkdir(exist_ok=True)
    listing=lists/'check.f';listing.write_text('--sdf-check ../test.sdf\n--emit-ir ../from-list.json\n')
    nested=lists/'nested.f';nested.write_text('-F check.f\n')
    p=run(['-F',nested])
    assert json.loads(p.stdout)==data==json.loads((out/'from-list.json').read_text())
    for target in [source,out/'sym.sdf',out/'hard.sdf']:
        if target!=source:
            target.unlink(missing_ok=True)
            if target.name=='sym.sdf':target.symlink_to(source)
            else:target.hardlink_to(source)
        run(['--sdf-check',source,'--emit-ir',target],False);assert source.read_bytes()==raw
    for args in [[],['--sdf-check'],['--sdf-check',source,'--sdf-check',source],
                 ['--sdf-check',source,'--gate-check'],['--sdf-check',source,'other.v'],
                 ['--sdf-check',source,'--wave-support'],['--sdf-check',source,'-E'],
                 ['--sdf-check',source,'--emit-cpp','x.cpp'],['--sdf-check',source,'-D','A=1']]:
        run(args,False)
    bad=out/'bad.sdf';bad.write_bytes(raw[:-3]);summary.unlink()
    p=run(['--sdf-check',bad,'--emit-ir',summary],False)
    assert not summary.exists() and 'bad.sdf:' in p.stderr and 'SDF:' in p.stderr
    print('PASS SDF CLI, independent mode, JSON, malformed diagnostics, symlink/hardlink input protection')
if __name__=='__main__':main()
