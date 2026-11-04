#!/usr/bin/env python3
import argparse,json,subprocess,sys
from pathlib import Path
from cases import CASES
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,timeline

def main():
 ap=argparse.ArgumentParser();ap.add_argument('compiler',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args()
 compiler=a.compiler.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
 def run(cmd,w,log,ok=True):
  p=subprocess.run(list(map(str,cmd)),cwd=w,capture_output=True,text=True,timeout=180);(w/log).write_text(p.stdout+p.stderr)
  assert (p.returncode==0) if ok else (p.returncode>0),(cmd,p.stdout,p.stderr)
  assert not any(t in p.stdout+p.stderr for t in ['AddressSanitizer','UndefinedBehaviorSanitizer','runtime error:','DEADLYSIGNAL']),(cmd,p.stdout,p.stderr)
  return p.stdout+p.stderr
 for name,(source,expected) in CASES.items():
  w=out/name;w.mkdir(exist_ok=True);(w/'top.v').write_text(source)
  run([compiler,w/'top.v','--wave-support','--emit-ir',w/'ir.json','--emit-preprocessed',w/'pp.v','-o',w/'native'],w,'compile.log')
  traces=[]
  for ext in ['vcd','dwf']:
   dest=w/('wave.'+ext);dest.unlink(missing_ok=True)
   text=run([w/'native','--waveform',dest,'--wave-format',ext],w,ext+'.log')
   assert text.splitlines()==expected,(name,text,expected)
   meta,events=read(dest);traces.append(timeline(meta,events))
   actual=json.loads((w/'ir.json').read_text())['global_precision_fs']
   scales={'fs':1,'ps':1000,'ns':10**6,'us':10**9,'ms':10**12,'s':10**15}
   raw=next(t[1] for t in meta['header'] if t[0]=='$timescale')
   import re
   n,u=re.fullmatch(r'(\d+)([a-z]+)',raw).groups();assert int(n)*scales[u]==actual,(name,raw,actual)
  assert traces[0]==traces[1]
  if name=='fractions':assert traces[0][('top','a')][2]==[(0,(0,0)),(1,(1,0)),(2,(0,0)),(15,(1,0)),(25,(0,0))],traces[0]
  run([compiler,w/'pp.v','--emit-ir',w/'roundtrip.json','-o',w/'roundtrip'],w,'roundtrip-compile.log')
  assert run([w/'roundtrip'],w,'roundtrip.log').splitlines()==expected
  assert json.loads((w/'roundtrip.json').read_text())['global_precision_fs']==actual
  run([w/'native','--waveform',w/'wrong.dwf','--wave-timescale','100s'],w,'mismatch.log',False)
  assert not (w/'wrong.dwf').exists()
  print('PASS timing',name,flush=True)
 # Numeric real contexts formerly rejected are now executed, with exact ticks.
 for name,body,wanted in [
  ('real_assign','reg [31:0] a;initial begin a=1.25;$display("TRACE a=%0d",a);end','TRACE a=1'),
  ('real_param','parameter A=1.25;initial begin #A;$display("TRACE t=%0t",$time);end','TRACE t=1000'),
  ('real_math','initial begin #(1.25+2);$display("TRACE t=%0t",$time);end','TRACE t=3000')]:
  w=out/name;w.mkdir(exist_ok=True)
  (w/'numeric.sv').write_text('`timescale 1ns/1ps\nmodule top;\n'+body+'\nendmodule\n')
  run([compiler,w/'numeric.sv','-o',w/name],w,name+'-compile.log')
  assert run([w/name],w,name+'.log').splitlines()==[wanted]
 w=out/'sized_concat';w.mkdir(exist_ok=True)
 (w/'top.sv').write_text('`timescale 1ns/1ps\nmodule top;initial begin #({2\'d1,2\'d2});$display("TRACE t=%0t",$time);end endmodule\n')
 run([compiler,w/'top.sv','-o',w/'native'],w,'compile.log')
 assert run([w/'native'],w,'run.log').splitlines()==['TRACE t=6000']
 # Cross-file compiler directive state and include / inactive macro behavior.
 w=out/'preprocessing';w.mkdir(exist_ok=True)
 (w/'a.v').write_text('`timescale 10ns/1ns\nmodule child;initial begin #1;$display("TRACE child=%0t",$time);end endmodule\n')
 (w/'b.v').write_text('module top;child c();initial begin #2;$display("TRACE top=%0t",$time);$finish;end endmodule\n')
 run([compiler,w/'a.v',w/'b.v','-o',w/'native'],w,'cross-compile.log')
 assert run([w/'native'],w,'cross.log').splitlines()==['TRACE child=10','TRACE top=20']
 (w/'scale.vh').write_text('`timescale 1ns/10ps\n')
 (w/'top.v').write_text('`ifdef DISABLED\n`timescale bad\n`endif\n`include "scale.vh"\nmodule top;initial begin #0.015;$display("TRACE t=%0t",$time);$finish;end endmodule\n')
 run([compiler,w/'top.v','-o',w/'native'],w,'include-compile.log');assert run([w/'native'],w,'include.log').splitlines()==['TRACE t=0']
 run([compiler,'--timescale','1ns/1ps',out/'default/top.v','--emit-ir',w/'default.json','-o',w/'native'],w,'cli-compile.log')
 assert run([w/'native'],w,'cli.log').splitlines()==['TRACE default d=1 t=1000']
 assert json.loads((w/'default.json').read_text())['global_precision_fs']==1000
 negatives={
  'coarse':'`timescale 1ps/1ns\nmodule top;endmodule',
  'invalid':'`timescale 3ns/1ps\nmodule top;endmodule',
  'inside':'module top;\n`timescale 1ns/1ps\nendmodule',
  'overflow':'`timescale 1s/1fs\nmodule top;initial begin #100000;$finish;end endmodule',
  'negative':'module top;initial begin #(-1);$finish;end endmodule',
  'concat':'module top;initial #({1,2,3});endmodule',
 }
 for name,source in negatives.items():
  (w/'bad.v').write_text(source);text=run([compiler,w/'bad.v','--emit-cpp',w/'bad.cpp'],w,name+'.log',False)
  assert 'syntax error' not in text,(name,text)
  assert ('overflow' in text) if name=='overflow' else True
 print('PASS timing preprocessing, CLI, overflow and real numeric contexts',flush=True)
if __name__=='__main__':main()
