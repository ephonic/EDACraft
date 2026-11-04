"""Actual CLI gate preprocessing, source maps, dependencies and protected outputs."""
from pathlib import Path
import json, os, subprocess, sys
compiler=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
lib=out/'cells.lib';lib.write_text('library(l){cell(B){pin(A){direction:input;}pin(Z){direction:output;function:"A";}}}\n')
net=out/'net.v';tb=out/'tb.v';inc=out/'include space';inc.mkdir(exist_ok=True)
tb.write_text('`timescale 1ns/1ps\nmodule top;reg a;wire z;dut d(a,z);initial begin a=0;#1;a=1;#1;$display("TRACE %b",z);$finish;end endmodule\n')
body='module dut(input a,output z); B u(.A(a),.Z(z)); endmodule\n'
def run(name,args,ok=True,cwd=out):
 p=subprocess.run(list(map(str,[compiler,*args])),cwd=cwd,text=True,capture_output=True,timeout=180)
 (out/(name+'.stdout')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
 assert (p.returncode==0)==ok,(name,p.stdout,p.stderr)
 return p
def gate():return ['--gate-netlist',net,'--gate-top','dut','--liberty',lib]
net.write_text('`timescale 1ps/1fs\n'+body+'`timescale 1fs/1fs\nmodule unused;endmodule\n')
p=run('header',gate()+[tb,'--emit-ir',out/'header.json','-o',out/'header'])
r=json.loads((out/'header.json').read_text());assert r['global_precision_fs']==1
assert r['gate_design']['gate_preprocessing']['fast_path']
p=subprocess.run([out/'header'],capture_output=True,text=True,check=True);assert 'TRACE 1' in p.stdout
# The unused fine-precision module must not lower the tick.
net.write_text('`timescale 1ns/10ps\n'+body+'`timescale 1ps/1fs\nmodule unused;endmodule\n')
run('unused',gate()+[tb,'--emit-ir',out/'unused.json','--emit-only','--emit-cpp',out/'unused.cpp'])
assert json.loads((out/'unused.json').read_text())['global_precision_fs']==1000
# An uninstantiated structural root is unused too.
net.write_text('`timescale 1ps/1fs\n'+body)
other=out/'no-dut.v';other.write_text('`timescale 1ns/1ps\nmodule top;initial begin #1;$display("TRACE %0t",$time);$finish;end endmodule\n')
run('unused-root',gate()+[other,'--emit-ir',out/'unused-root.json','--emit-only','--emit-cpp',out/'unused-root.cpp'])
assert json.loads((out/'unused-root.json').read_text())['global_precision_fs']==1000
# Escaped structural module names must receive the same scope-time override.
net.write_text('`timescale 1ps/1fs\n'+body.replace('module dut','module \\d.u '))
escaped=out/'escaped-tb.v';escaped.write_text(tb.read_text().replace('dut d','\\d.u  d'))
run('escaped-root',['--gate-netlist',net,'--gate-top','d.u','--liberty',lib,escaped,'--emit-ir',out/'escaped.json','--emit-only','--emit-cpp',out/'escaped.cpp'])
escaped_ir=json.loads((out/'escaped.json').read_text())
assert escaped_ir['global_precision_fs']==1 and escaped_ir['scopes'][1]['time_unit_fs']==1000
child=inc/'child.v';child.write_text('`timescale 10ps/1ps\nmodule leaf(input a,output z); `CELL u(.A(a),.Z(z)); endmodule\n')
net.write_text('`include "child.v"\n`ifdef USE_CHILD\nmodule dut(input a,output z);leaf c(a,z);endmodule\n`else\nmodule dut;endmodule\n`endif\n')
args=['-I',inc,'-DCELL=B','-DUSE_CHILD']
run('macros',args+gate()+[tb,'--emit-ir',out/'macros.json','--emit-deps',out/'deps.json','-o',out/'macros'])
r=json.loads((out/'macros.json').read_text());assert not r['gate_design']['gate_preprocessing']['fast_path']
assert r['gate_design']['structural_precision_fs']==1000
deps=json.loads((out/'deps.json').read_text());assert str(child.resolve()) in deps['dependencies']
assert str(net.resolve()) in deps['dependencies'] and deps['gate_preprocessing']['modules'][0]['name']=='leaf'
p=subprocess.run([out/'macros'],capture_output=True,text=True,check=True);assert 'TRACE 1' in p.stdout
sdf=out/'binding.sdf';sdf.write_text('(DELAYFILE (SDFVERSION "3.0") (DIVIDER /) (TIMESCALE 1ps) (CELL (CELLTYPE "B") (INSTANCE c/u) (DELAY (ABSOLUTE (IOPATH A Z (1))))))')
p=run('macro-binding',args+gate()+['--sdf-bind-check',sdf,'--sdf-tick','1ps','--timescale','1ns/1ps'])
assert json.loads(p.stdout)['bound_entries']==1
protected=out/'protected.cpp';report=out/'protected.json'
def reject(name,extra,needle):
 protected.write_text('keep-cpp');report.write_text('keep-ir')
 p=run(name,extra+gate()+[tb,'--emit-only','--emit-cpp',protected,'--emit-ir',report],False)
 assert needle in p.stderr,(name,p.stderr)
 assert protected.read_text()=='keep-cpp' and report.read_text()=='keep-ir'
child.write_text('// original line 1\nmodule leaf(input a,output z);\nwire t;\nassign z=a&1\'b1;\nendmodule\n')
reject('included-syntax',args,'child.v:4:')
child.write_text('`timescale 1ps/1ps\nmodule leaf(input a,output z); B u(.A(a),.Z(z)); endmodule\n')
original=child.read_bytes()
p=run('include-overwrite',args+gate()+[tb,'--emit-only','--emit-cpp',child],False)
assert 'overwrite an input' in p.stderr and child.read_bytes()==original
alias=out/'included-hardlink.v';alias.unlink(missing_ok=True);os.link(child,alias)
p=run('hardlink-overwrite',args+gate()+[tb,'--emit-only','--emit-cpp',alias],False)
assert 'overwrite an input' in p.stderr and child.read_bytes()==original
for name,text,needle in [
 ('invalid-scale','`timescale 1ps/10ps\n'+body,'precision'),
 ('scale-in-module','module dut;\n`timescale 1ns/1ps\nendmodule\n','outside a module'),
 ('unknown-directive','`default_nettype none\n'+body,'not supported'),
 ('missing-include','`include "missing-net.v"\n'+body,'include file not found'),
 ('undefined-macro','module dut;`MISSING u();endmodule\n','undefined macro'),
 ('conditional','`ifdef X\n'+body,'unterminated conditional'),
 ('comment','/* unterminated','unterminated block comment'),
]:
 net.write_text(text);reject(name,[],needle)
(out/'results.json').write_text(json.dumps({'status':'PASS','scope':'actual CLI structural preprocessing, timing/global precision, macro/include, original source diagnostics, dependencies, same-path/hardlink input protection and strict unsupported failures'},indent=2)+'\n')
print('PASS actual gate-source CLI, timing, diagnostics, dependencies and protected outputs')
