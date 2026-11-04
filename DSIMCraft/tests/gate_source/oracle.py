"""Fresh VCS reference for structural-module timing, without rewriting inputs."""
from pathlib import Path
import argparse, hashlib, json, subprocess

def make(out):
    body='module dut(input a,output z);B u(.A(a),.Z(z));endmodule\n'
    cases={
        'root-fine': '`timescale 1ps/1fs\n'+body,
        'unused-fine': '`timescale 1ns/10ps\n'+body+'`timescale 1ps/1fs\nmodule unused;endmodule\n',
        'nested-fine': '`timescale 1ns/10ps\nmodule dut(input a,output z);leaf c(a,z);endmodule\n`timescale 10ps/1fs\nmodule leaf(input a,output z);B u(.A(a),.Z(z));endmodule\n',
        'macro-include': '`include "child.v"\n`ifdef USE_CHILD\nmodule dut(input a,output z);leaf c(a,z);endmodule\n`else\nmodule dut(input a,output z);endmodule\n`endif\n',
    }
    for name,net in cases.items():
        w=out/name;w.mkdir(parents=True,exist_ok=True)
        (w/'net.v').write_text(net)
        (w/'child.v').write_text('`timescale 100ps/10fs\nmodule leaf(input a,output z);`CELL u(.A(a),.Z(z));endmodule\n')
        (w/'cells.lib').write_text('library(l){cell(B){pin(A){direction:input;}pin(Z){direction:output;function:"A";}}}\n')
        (w/'cells.v').write_text('`timescale 1ns/1ns\nmodule B(input A,output Z);assign Z=A;endmodule\n')
        (w/'tb.v').write_text('`timescale 1ns/1ps\nmodule top;reg a;wire z;dut d(a,z);\n`ifdef VCS_REFERENCE\ninitial begin $dumpfile("vcs.vcd");$dumpvars(0,top);end\n`endif\ninitial begin a=0;#1;a=1;#1;$display("TRACE t=%0t z=%b",$time,z);$finish;end endmodule\n')
    return cases

def main():
    ap=argparse.ArgumentParser();ap.add_argument('out',type=Path);ap.add_argument('--native',type=Path);args=ap.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    cases=make(out);results={'status':'RUNNING','cases':{},'repeat':3}
    def save():(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    def run(cmd,w,label):
        p=subprocess.run(list(map(str,cmd)),cwd=w,text=True,capture_output=True,timeout=300)
        (w/(label+'.log')).write_text(p.stdout+p.stderr)
        assert p.returncode==0,(label,p.stdout,p.stderr)
        return [s for s in p.stdout.splitlines() if s.startswith('TRACE ')]
    try:
        for name in cases:
            w=out/name
            if args.native:
                flags=['-I',w,'-DCELL=B','-DUSE_CHILD'] if name=='macro-include' else []
                cmd=[args.native.resolve(),*flags,'--gate-netlist',w/'net.v','--gate-top','dut','--liberty',w/'cells.lib',w/'tb.v','--emit-ir',w/'native.json','-o',w/'native']
                tool='native'
            else:
                flags=['+incdir+.', '+define+CELL=B','+define+USE_CHILD'] if name=='macro-include' else []
                cmd=['vcs','-full64','-sverilog','-top','top','+define+VCS_REFERENCE',*flags,'cells.v','net.v','tb.v','-o',w/'simv']
                tool='vcs'
            run(cmd,w,tool+'-compile')
            binary=w/('native' if args.native else 'simv');traces=[]
            for i in range(3):
                traces.append(run([binary],w,f'{tool}-{i}'))
                if not args.native:(w/'vcs.vcd').rename(w/f'{i}-vcs.vcd')
            assert traces[0] and traces.count(traces[0])==3,(name,traces)
            results['cases'][name]={'trace':traces[0],'command':list(map(str,cmd)),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
            if args.native:
                expected=json.loads((out/'vcs-results.json').read_text())['cases'][name]['trace']
                assert traces[0]==expected,(name,traces[0],expected)
            save();print('PASS',tool,'structural time',name,flush=True)
        results['status']='PASS';save()
    except Exception as e:results['status']='FAIL';results['error']=str(e);save();raise
if __name__=='__main__':main()
