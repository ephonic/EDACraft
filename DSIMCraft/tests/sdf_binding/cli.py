#!/usr/bin/env python3
import argparse,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('compiler',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();compiler=a.compiler.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
 def run(args,label,ok=True):
  p=subprocess.run(list(map(str,[compiler,*args])),cwd=out,text=True,capture_output=True,timeout=90);(out/(label+'.log')).write_text(p.stdout+p.stderr)
  assert (p.returncode==0) if ok else (p.returncode>0),(args,p.stdout,p.stderr)
  assert not any(t in p.stdout+p.stderr for t in ['AddressSanitizer','UndefinedBehaviorSanitizer','runtime error:','DEADLYSIGNAL'])
  return p
 base=['--sdf-bind-check',ROOT/'tests/sdf_binding/timing.sdf','--gate-netlist',ROOT/'tests/sdf_binding/net.v','--gate-top','dut','--liberty',ROOT/'tests/gate/cells.lib','--sdf-tick','1ps']
 for corner,missing in [('min',0),('typ',1),('max',0)]:
  p=run([*base,'--sdf-corner',corner,'--emit-ir',out/'result.json'],corner);r=json.loads(p.stdout)
  assert json.loads((out/'result.json').read_text())==r and r['corner']==corner and r['binding'] and not r['annotation']
  assert r['bound_entries']==16 and r['missing_selected_values']==missing and r['negative_selected_values']==1
 (out/'base.sdf').write_text('(DELAYFILE (SDFVERSION "3.0") (DIVIDER /) (TIMESCALE 1ns) (CELL (CELLTYPE "INV") (INSTANCE v) (DELAY (ABSOLUTE (IOPATH A Y (1))))))')
 args=base.copy();args[1]=out/'base.sdf'
 source=(out/'base.sdf').read_text()
 negatives={
  'instance':source.replace('(INSTANCE v)','(INSTANCE missing)'),
  'type':source.replace('CELLTYPE "INV"','CELLTYPE "XOR2"'),
  'port':source.replace('IOPATH A Y','IOPATH BAD Y'),
  'direction':source.replace('IOPATH A Y','IOPATH Y A'),
  'hier_port':source.replace('IOPATH A Y','IOPATH h/u/A Y'),
  'wildcard':source.replace('(CELLTYPE "INV") (INSTANCE v)','(CELLTYPE "MISSING") (INSTANCE *)'),
  'not_connected':source.replace('(CELLTYPE "INV") (INSTANCE v)','(CELLTYPE "dut") (INSTANCE)').replace('IOPATH A Y','INTERCONNECT a literal\\/slash/A'),
  'wrong_source':source.replace('(CELLTYPE "INV") (INSTANCE v)','(CELLTYPE "dut") (INSTANCE)').replace('IOPATH A Y','INTERCONNECT v/A y'),
  'wrong_dest':source.replace('(CELLTYPE "INV") (INSTANCE v)','(CELLTYPE "dut") (INSTANCE)').replace('IOPATH A Y','INTERCONNECT a v/Y'),
  'escaped_is_atomic':source.replace('(INSTANCE v)','(INSTANCE literal/slash)'),
  'empty_component':source.replace('(INSTANCE v)','(INSTANCE h//u)'),
  'missing_unit':source.replace('(TIMESCALE 1ns)',''),
  'overflow':source.replace('(1))))))','(1e100))))))'),
  'late_error':source[:-1]+' (CELL (CELLTYPE "INV") (INSTANCE MISSING)))',
 }
 (out/'protected.json').write_text('sentinel')
 for name,text in negatives.items():
  (out/'bad.sdf').write_text(text);cmd=args.copy();cmd[1]=out/'bad.sdf'
  p=run([*cmd,'--emit-ir',out/'protected.json'],name,False)
  assert 'SDF binding:' in p.stderr,(name,p.stderr)
  assert (out/'protected.json').read_text()=='sentinel'
 # Explicit unit fallback and preservation of quoted/escaped names.
 (out/'bad.sdf').write_text(negatives['missing_unit']);cmd=args.copy();cmd[1]=out/'bad.sdf'
 assert json.loads(run([*cmd,'--sdf-unit','1ns'],'fallback').stdout)['unit_fs']==10**6
 p=run([*args,'--sdf-unit','1ps'],'header-wins');assert json.loads(p.stdout)['unit_fs']==10**6
 # A different divider changes hierarchy, while escaped separators stay atomic.
 text=(ROOT/'tests/sdf_binding/timing.sdf').read_text().replace('(DIVIDER /)','(DIVIDER .)')
 for old,new in [('h/u','h.u'),('h/a','h.a'),('h/y','h.y'),('v/A','v.A'),('v/Y','v.Y'),('u/A','u.A'),('slash/A','slash.A')]:text=text.replace(old,new)
 (out/'dot.sdf').write_text(text);dot=base.copy();dot[1]=out/'dot.sdf'
 assert json.loads(run(dot,'dot-divider').stdout)['bound_entries']==16
 # Structural assigns are directed: sharing a weakly connected component
 # does not establish a path from an output back to an earlier receiver.
 (out/'directed.v').write_text('module dut(input a,b,output y,z);wire n;assign n=a;INV u(.A(a),.Y(y));INV v(.A(b),.Y(n));assign z=n;endmodule')
 (out/'directed.sdf').write_text('(DELAYFILE (SDFVERSION "3.0") (TIMESCALE 1ps) (DIVIDER /) (CELL (CELLTYPE "dut") (INSTANCE) (DELAY (ABSOLUTE (INTERCONNECT v/Y z (1))))))')
 directed=base.copy();directed[1]=out/'directed.sdf';directed[3]=out/'directed.v'
 assert json.loads(run(directed,'directed-forward').stdout)['interconnects']==1
 (out/'directed.sdf').write_text((out/'directed.sdf').read_text().replace('v/Y z','v/Y u/A'))
 assert 'not connected' in run(directed,'directed-reverse',False).stderr
 # Topology-only mode accepts non-executable models, ascending/wide root ports.
 (out/'pins.lib').write_text('library(p) {cell(P) {pin(A) {direction: input;}pin(Y) {direction: output;}}}')
 (out/'wide.v').write_text('module dut(input [0:127] a,output [127:0] y);P u(.A(a[127]),.Y(y[0]));endmodule')
 (out/'wide.sdf').write_text('(DELAYFILE (SDFVERSION "3.0") (TIMESCALE 1ps) (DIVIDER /) (CELL (CELLTYPE "dut") (INSTANCE) (DELAY (ABSOLUTE (INTERCONNECT a[127] u/A (1)) (INTERCONNECT u/Y y[0] (1))))))')
 wide=['--sdf-bind-check',out/'wide.sdf','--gate-netlist',out/'wide.v','--gate-top','dut','--liberty',out/'pins.lib','--sdf-tick','1ps']
 assert json.loads(run(wide,'wide').stdout)['interconnects']==2
 run(['--gate-check','--gate-netlist',out/'wide.v','--gate-top','dut','--liberty',out/'pins.lib'],'wide-functional',False)
 # Liberty's internal direction must never fall through to input direction.
 (out/'pins.lib').write_text((out/'pins.lib').read_text().replace('direction: input','direction: internal'))
 assert 'internal Liberty pin' in run(wide,'internal-pin',False).stderr
 # Gate preprocessing/time options are valid in topology-only mode too.
 assert json.loads(run([*base,'--timescale','1ns/1ps','-DUNUSED=1','-UUNUSED','-I',out],'preprocessing-flags').stdout)['bound_entries']==16
 for i,extra in enumerate([['--sdf-corner','bad'],['--sdf-tick','3ps'],['--wave-support'],['--gate-check']]):run([*base,*extra],f'flags-{i}',False)
 run(base[:-2],'missing-tick',False)
 run(['--sdf-corner','min',ROOT/'tests/sdf_binding/net.v'],'orphan-flags',False)
 # Every input and file-list path is protected against direct/symlink/hardlink output clobber.
 for path in [ROOT/'tests/sdf_binding/timing.sdf',ROOT/'tests/sdf_binding/net.v',ROOT/'tests/gate/cells.lib']:
  before=path.read_bytes();run([*base,'--emit-ir',path],path.suffix+'-clobber',False);assert path.read_bytes()==before
 target=out/'alias.sdf';target.unlink(missing_ok=True);target.symlink_to(out/'base.sdf');before=(out/'base.sdf').read_bytes()
 run([*args,'--emit-ir',target],'symlink-clobber',False);assert (out/'base.sdf').read_bytes()==before
 target=out/'hard.sdf';target.unlink(missing_ok=True);os.link(out/'base.sdf',target)
 run([*args,'--emit-ir',target],'hardlink-clobber',False);assert (out/'base.sdf').read_bytes()==before
 (out/'args.f').write_text(' '.join(map(str,['--sdf-bind-check','base.sdf','--gate-netlist',ROOT/'tests/sdf_binding/net.v','--gate-top','dut','--liberty',ROOT/'tests/gate/cells.lib','--sdf-tick','1ps','--sdf-corner','max'])))
 assert json.loads(run(['-F',out/'args.f'],'filelist').stdout)['corner']=='max'
 print('PASS SDF binding CLI: corners, strict failures, fallback, wide topology, flags, paths and file lists',flush=True)
if __name__=='__main__':main()
