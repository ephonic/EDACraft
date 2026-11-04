"""End-to-end timing-check fixtures, shared by native and fresh VCS runs."""
from pathlib import Path
import json

def make(base):
 base=Path(base);base.mkdir(parents=True,exist_ok=True);cases={}
 stimulus="C=0;D=0;E=1;#100;D=1;#2;C=1;#1;D=0;#2;C=0;#3;C=1;#7;C=0;#1;D=1;#10;C=1;#2;D=0;#6;C=0;#5;"
 definitions=[('setup','SETUP','D,posedge C,5','D (posedge C) (5)'),('hold','HOLD','posedge C,D,5','D (posedge C) (5)'),('recovery','RECOVERY','D,posedge C,5','D (posedge C) (5)'),('removal','REMOVAL','D,posedge C,5','D (posedge C) (5)'),('setuphold','SETUPHOLD','posedge C,D,5,5','D (posedge C) (5) (5)'),('recrem','RECREM','D,posedge C,5,5','D (posedge C) (5) (5)'),('width','WIDTH','posedge C,5,0','(posedge C) (5)'),('period','PERIOD','posedge C,10','(posedge C) (10)'),('skew','SKEW','posedge C,D,5','(posedge C) D (5)')]
 # SDF SKEW uses the reference first, unlike setup/hold. The implementation
 # canonicalizes it on input; this fixture also exercises source order.
 for name,kind,args,sdf_event in definitions:
  cases[name]=dict(kind=kind,args=args,sdf=f'({kind} {sdf_event})',stimulus=stimulus)
 cases['condition']=dict(kind='SETUP',args='D &&& E,posedge C,5',sdf="(SETUP (COND E D) (posedge C) (5))",stimulus=stimulus+"E=0;#10;D=1;#1;C=1;#10;E=1'bx;D=0;#1;C=0;#1;C=1;#10;")
 cases['threshold']=dict(kind='WIDTH',args='posedge C,5,2',sdf='(WIDTH (posedge C) (5))',stimulus=stimulus)
 cases['edge-overrides']=dict(kind='HOLD',args='posedge C,D,0',sdf='(HOLD (posedge D) (posedge C) (7)) (HOLD (negedge D) (posedge C) (2))',stimulus=stimulus)
 cases['negative']=dict(kind='HOLD',args='posedge C,D,2',sdf='(HOLD D (posedge C) (-5))',stimulus=stimulus)
 cases['delta']=dict(kind='SETUPHOLD',args='posedge C,D,5,5',sdf='(SETUPHOLD D (posedge C) (5) (5))',stimulus="C=0;D=0;E=1;#100;D=1;C=1;D=0;#0;D=1;C=0;C=1;#10;")
 cases['setup-edge-overrides']=dict(kind='SETUP',args='D,posedge C,3',sdf='(SETUP (posedge D) (posedge C) (8)) (SETUP (negedge D) (posedge C) (1))',stimulus=stimulus)
 cases['fourstate']=dict(kind='SETUPHOLD',args='posedge C,D,0,0',sdf='(SETUPHOLD D (posedge C) (5) (5))',stimulus="C=0;D=0;E=1;#100;C=1'bx;#1;D=1'bz;#1;C=1;#1;D=1'bx;#10;C=0;#1;D=1;#1;C=1'bz;#1;D=0;#10;")
 cases['explicit-edge']=dict(kind='HOLD',args='posedge C,edge [01] D,0',sdf='(HOLD (01 D) (posedge C) (5))',stimulus="C=0;D=0;E=1;#100;C=1;#1;D=1;#10;D=0;C=0;#10;C=1;#1;D=1'bx;#10;")
 cases['composed']=dict(kind='HOLD',args='posedge C,D,0',sdf='(HOLD D (posedge C) (5))',stimulus=stimulus)
 cases['combined-split']=dict(kind='SETUPHOLD',args='posedge C,D,0,0',sdf='(SETUP D (posedge C) (5)) (HOLD D (posedge C) (7))',stimulus=stimulus)
 cases['setup-zero']=dict(kind='SETUP',args='D,posedge C,0',sdf='(SETUP D (posedge C) (5))',stimulus="C=0;D=0;E=1;#100;D=1;C=1;#0;D=0;#10;")
 cases['hold-zero']=dict(kind='HOLD',args='posedge C,D,0',sdf='(HOLD D (posedge C) (5))',stimulus="C=0;D=0;E=1;#100;D=1;C=1;#0;D=0;#10;")
 for name,c in cases.items():
  w=base/name;w.mkdir(exist_ok=True)
  check='$'+c['kind'].lower()
  args=c['args'];before=args.rsplit(',',1)[0]+',0' if c['kind'] not in ['SETUPHOLD','RECREM','WIDTH'] else args
  # Keep default limits different from SDF in most cases to verify annotation.
  if name not in ['threshold','negative','edge-overrides']:
   n=2 if c['kind'] in ['SETUPHOLD','RECREM'] else 1
   tokens=args.split(',');start=1 if c['kind'] in ['WIDTH','PERIOD'] else 2
   for i in range(n):tokens[start+i]='0'
   before=','.join(tokens)
  else:before=args
  model=f"`timescale 1ps/1ps\nmodule CELL(input C,D,E,output Z);assign Z=D;\n`ifdef VCS_REFERENCE\nreg notifier=0;always @(notifier) if($time>0) $display(\"CHECK kind={c['kind']} time=%0t\",$time);\n`endif\nspecify (D=>Z)=0;\n`ifdef VCS_REFERENCE\n{check}({before},notifier);\n`else\n{check}({before});\n`endif\nendspecify endmodule\n"
  # WIDTH notifier is its fourth argument; insert optional threshold when omitted.
  if c['kind']=='WIDTH' and len(before.split(','))==2:model=model.replace(before+',notifier',before+',0,notifier')
  if name in ['edge-overrides','setup-edge-overrides']:
   args0=['posedge C,posedge D,0','posedge C,negedge D,0'] if name=='edge-overrides' else ['posedge D,posedge C,0','negedge D,posedge C,0']
   model=model.replace(check+'('+before+',notifier);','\n'.join(check+'('+x+',notifier);' for x in args0))
   model=model.replace(check+'('+before+');','\n'.join(check+'('+x+');' for x in args0))
  (w/'cells.v').write_text(model)
  (w/'cells.lib').write_text('library(l){cell(CELL){pin(C){direction:input;}pin(D){direction:input;}pin(E){direction:input;}pin(Z){direction:output;function:"D";}}}\n')
  (w/'net.v').write_text('module dut(input C,D,E,output Z);CELL u(.C(C),.D(D),.E(E),.Z(Z));endmodule\n')
  (w/'delay.sdf').write_text('(DELAYFILE (SDFVERSION "3.0") (DIVIDER /) (TIMESCALE 1ps) (CELL (CELLTYPE "CELL") (INSTANCE u) (TIMINGCHECK '+c['sdf']+')))\n')
  if name=='composed':
   (w/'delay.sdf').write_text('(DELAYFILE (SDFVERSION "3.0") (DIVIDER /) (TIMESCALE 1ps) (CELL (CELLTYPE "dut") (INSTANCE) (DELAY (ABSOLUTE (INTERCONNECT D u/D (3))))) (CELL (CELLTYPE "CELL") (INSTANCE u) (DELAY (ABSOLUTE (IOPATH D Z (2)))) (TIMINGCHECK '+c['sdf']+')))\n')

  (w/'tb.v').write_text('`timescale 1ps/1ps\nmodule top;reg C,D,E;wire Z;dut d(C,D,E,Z);\n`ifdef VCS_REFERENCE\ninitial begin $sdf_annotate("delay.sdf",d,,"annotation.log","TYPICAL");$dumpfile("vcs.vcd");$dumpvars(0,top);end\n`endif\ninitial begin '+c['stimulus']+'$display("TRACE done c=%b d=%b",C,D);$finish;end endmodule\n')
 (base/'cases.json').write_text(json.dumps(cases,indent=2)+'\n');return cases
if __name__=='__main__':
 import sys
 make(sys.argv[1])
