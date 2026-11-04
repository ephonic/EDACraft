"""Execute the actual CLI for all previous 54 VCS numeric oracle cases."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
base=ROOT/'tests/sdf_path';rows=json.loads((base/'oracles.json').read_text())['cases'];results={}
values=['0','1',"1'bz","1'bx",'0',"1'bx",'1',"1'bx","1'bz",'0',"1'bz",'1','0']
for row in rows:
 w=out/row['name'];w.mkdir(exist_ok=True)
 (w/'cells.v').write_text('`timescale '+row['scale']+'\nmodule B(input A,output Z); assign Z=A;specify (A=>Z)=('+row['base']+');endspecify endmodule\n')
 (w/'cells.lib').write_text((base/'buffer.lib').read_text().replace('cell(BUF)','cell(B)'))
 (w/'net.v').write_text('module dut(input A,output Z);B u(.A(A),.Z(Z));endmodule\n')
 original=(base/row['sdf']).read_bytes();assert hashlib.sha256(original).hexdigest()==row['input_sha256']
 (w/'delay.sdf').write_text(original.decode().replace('(INSTANCE)','(INSTANCE u)'))
 (w/'tb.v').write_text('`timescale 1ps/1ps\nmodule top;reg a;wire z;dut d(a,z);always @(z)$display("TRACE t=%0t z=%b",$time,z);initial begin #1000;'+''.join('a='+v+';#100;' for v in values)+'$finish;end endmodule\n')
 cmd=[compiler,'--sdf-annotate',w/'delay.sdf','--gate-models',w/'cells.v','--gate-netlist',w/'net.v','--gate-top','dut','--liberty',w/'cells.lib',w/'tb.v','--emit-ir',w/'ir.json','-o',w/'native']
 p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=180);(w/'compile.log').write_text(p.stdout+p.stderr)
 if row.get('unsupported'):
  assert p.returncode and 'unsupported VCS readback' in p.stderr and not (w/'ir.json').exists() and not (w/'native').exists(),(row['name'],p.stderr)
  results[row['name']]={'status':'REJECTED'};continue
 assert p.returncode==0,(row['name'],p.stdout,p.stderr)
 ir=json.loads((w/'ir.json').read_text());assert ir['global_precision_fs']==1000
 traces=[]
 for i in range(3):
  p=subprocess.run([w/'native'],capture_output=True,text=True,timeout=60);(w/f'run-{i}.log').write_text(p.stdout+p.stderr)
  assert p.returncode==0 and p.stdout.splitlines()==row['expected'],(row['name'],p.stdout,row['expected'],p.stderr);traces.append(p.stdout)
 assert len(set(traces))==1;results[row['name']]={'status':'PASS','trace':row['expected']}
 print('PASS CLI SDF numeric',row['name'],flush=True)
assert sum(r['status']=='PASS' for r in results.values())==54 and sum(r['status']=='REJECTED' for r in results.values())==4
(out/'results.json').write_text(json.dumps({'status':'PASS','cases':results,'scope':'Actual CLI execution against previous immutable VCS numeric references, not freshly run VCS.'},indent=2)+'\n')
