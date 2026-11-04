"""Unchanged shared RTL/SDF inputs for native and VCS static-task comparisons."""
from pathlib import Path
import json,sys,shutil

def make(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 # Import by file to avoid importing this module recursively as 'cases'.
 import importlib.util
 spec=importlib.util.spec_from_file_location('path_cases',Path(__file__).resolve().parents[1]/'sdf_runtime/cases.py')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 module.make(out/'fixtures');source=out/'fixtures/twelve'
 original=(source/'tb.v').read_text();a=original.index('`ifdef VCS_REFERENCE');b=original.index('`endif',a)+len('`endif')
 original=original[:a]+'ANNOTATION\n`ifdef VCS_REFERENCE\ninitial begin $dumpfile("vcs.vcd");$dumpvars(0,top);end\n`endif\n'+original[b:]
 requests={
  'direct':('initial $sdf_annotate("delay.sdf",d);',[],1),
  'third-config':('initial begin $display("ANNOTATE");$sdf_annotate("delay.sdf",d,"missing-config.log");end',[],1),
  'parameter-log':('localparam string SDF="delay.sdf";initial begin:setup localparam string UNUSED="annotation.log";$sdf_annotate(SDF,d,,"annotation.log","TYPICAL");end',[],1),
  'minimum':('initial $sdf_annotate("delay.sdf",d,,"annotation.log","MINIMUM");',[],0),
  'maximum-jobs':('initial $sdf_annotate("delay.sdf",d,,"annotation.log","MAXIMUM",,);',['--gate-scalar-timing','--gate-sdf-jobs','--time-wheel','--gate-path-dictionary'],2),
  'hierarchy':('initial $sdf_annotate("delay.sdf",w.d,,"annotation.log","TOOL_CONTROL");',[],1),
  'generate':('if(1)begin:cfg initial $sdf_annotate("delay.sdf",d);end',['--threads','2'],1),
  'finer-model':('initial $sdf_annotate("delay.sdf",d);',[],1),
 }
 result={}
 import re
 for name,(call,flags,corner) in requests.items():
  w=out/name;w.mkdir(exist_ok=True)
  for f in ['cells.v','cells.lib','net.v','delay.sdf']:shutil.copyfile(source/f,w/f)
  text=original.replace('ANNOTATION',call)
  if name=='hierarchy':text=text.replace('dut d(A,Z);','wrapper w(A,Z);')+'\nmodule wrapper(input A,output Z);dut d(A,Z);endmodule\n'
  if name=='finer-model':text=text.replace('1ps/1ps','1ns/1ns')
  if name in ('minimum','maximum-jobs'):
   sdf=(w/'delay.sdf').read_text()
   sdf=re.sub(r'\((\d+)\)',lambda m:'('+str(int(m[1]))+':'+str(int(m[1])+3)+':'+str(int(m[1])+6)+')',sdf)
   (w/'delay.sdf').write_text(sdf)
  (w/'tb.v').write_text(text);(w/'baseline.v').write_text(text.replace(call,''))
  result[name]=dict(flags=flags,corner=corner,task=call,log='annotation.log' in call)
 (out/'cases.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':make(sys.argv[1])
