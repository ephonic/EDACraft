#!/usr/bin/env python3
"""Clocked nonuniform XOR feedback networks: separate generate/compile/run costs."""
import argparse,hashlib,json,platform,re,statistics,subprocess
from pathlib import Path
from compare_vcs import ROOT,timed

def workload(size,cycles):
    assert size>=2 and cycles>=1
    bits=min(size,64);sample=[i*(size-1)//(bits-1) for i in range(bits)]
    left=[(i-1)%size for i in range(size)];right=[(i*73+19)%size for i in range(size)]
    net=[f'module dut(input c,a,r,output [{bits-1}:0] y);']
    for i in range(size):net.append(f'wire q{i},d{i};')
    for i in range(size):
        a='a' if i==0 else f'q{left[i]}'
        net.append(f'XOR2 x{i}(.A({a}),.B(q{right[i]}),.Y(d{i}));')
        net.append(f'DFFR f{i}(.C(c),.D(d{i}),.R(r),.Q(q{i}));')
    net+=['assign y={'+','.join(f'q{i}' for i in reversed(sample))+'};','endmodule']
    tb=f'''module top;
reg c,a,r; reg [31:0] i; reg [63:0] sum; wire [{bits-1}:0] y;
dut u(c,a,r,y);
initial begin
 c=0;a=0;r=1;sum=0;#1;r=0;#1;
 for(i=0;i<32'd{cycles};i=i+32'd1) begin
  a=~a;#1;c=1;#1;sum=sum+y;c=0;#1;
 end
 $display("TRACE sum=%h y=%h time=%0d",sum,y,$time);
 $finish;
end endmodule
'''
    # Scalar Boolean recurrence, independent of the simulator and parser.
    q=bytearray(size);total=0;value=0;activity=0
    for cycle in range(cycles):
        q=bytearray(((cycle+1)%2 if i==0 else q[left[i]])^q[right[i]] for i in range(size))
        value=sum(q[index]<<i for i,index in enumerate(sample));total=(total+value)&((1<<64)-1)
        activity+=sum(q)
    expected=[f'TRACE sum={total:016x} y={value:0{(bits+3)//4}x} time={2+3*cycles}']
    metadata=dict(flip_flops=size,xor_cells=size,sampling_copy_cells=1,total_gate_instances=2*size+1,sampled_bits=bits,sampled_indices=sample,
                  tap_definition='left=(i-1)%N, right=(73*i+19)%N, left of cell 0 is alternating external input',
                  oracle_one_samples=activity,initial_state=0,ideal_power=True,zero_delay=True)
    return '\n'.join(net)+'\n',tb,expected,metadata

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dsim',type=Path,default=ROOT/'build/dsim');ap.add_argument('--output',type=Path,default=ROOT/'build/benchmark-sequential')
    ap.add_argument('--sizes',type=int,nargs='+',default=[1000,10000,100000]);ap.add_argument('--cycles',type=int,default=200);ap.add_argument('--repeat',type=int,default=3)
    args=ap.parse_args()
    if min(args.sizes)<2 or args.cycles<1 or args.repeat<1:ap.error('sizes >=2, cycles/repeat positive')
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    libs=[ROOT/'tests/gate/cells.lib',ROOT/'tests/gate/sequential.lib'];models=[ROOT/'tests/gate/cells.v',ROOT/'tests/gate/sequential.v']
    report=dict(host=platform.node(),platform=platform.platform(),dsim_version=subprocess.check_output([args.dsim,'--version'],text=True).strip(),
                vcs_version=subprocess.check_output(['vcs','-full64','-ID'],text=True,stderr=subprocess.STDOUT),
                cxx_version=subprocess.check_output(['c++','--version'],text=True),repeat=args.repeat,cycles=args.cycles,
                warmup_runs_per_tool=1,native_flags=['-std=c++17','-O2'],vcs_flags=['-full64','-sverilog','-top','top'],
                library_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in libs+models},cases={},
                note='Own loads serial; one warmup/tool then alternating measured order. Shared host; affinity/frequency uncontrolled. A deterministic two-state feedback benchmark for ideal Liberty storage; not timing/power/foundry-model equivalence or general VCS parity.')
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        for size in args.sizes:
            work=out/f'size-{size}';work.mkdir(exist_ok=True)
            net,tb,expected,metadata=workload(size,args.cycles)
            source,testbench=work/'input.v',work/'tb.v';source.write_text(net);testbench.write_text(tb)
            record=dict(status='RUNNING',netlist_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),tb_sha256=hashlib.sha256(testbench.read_bytes()).hexdigest(),trace=expected,workload=metadata)
            report['cases'][str(size)]=record;save()
            native,vcs=work/'dsim_simv',work/'vcs_simv'
            generate=[args.dsim.resolve(),'--gate-netlist',source,'--gate-top','dut',testbench,'--emit-only','--emit-cpp',work/'model.cpp','--emit-ir',work/'ir.json']
            for lib in libs:generate+=['--liberty',lib]
            commands=dict(generate=generate,native_compile=['c++','-std=c++17','-O2',work/'model.cpp','-o',native],
                          vcs_compile=['vcs',*report['vcs_flags'],source,testbench,*models,'-o',vcs])
            record['commands']={key:[str(x) for x in cmd] for key,cmd in commands.items()}
            for key,cmd in commands.items():record[key],_=timed(cmd,work,key,timeout=900)
            record['generated_bytes']=(work/'model.cpp').stat().st_size
            ir=json.loads((work/'ir.json').read_text());assert ir['gate_design']['instance_count']==2*size+1 and ir['gate_design']['sequential_instance_count']==size and len(ir['scopes'])==2
            runs=dict(dsim=[native,'--max-events',str(max(10000000,size*args.cycles*100))],vcs=[vcs])
            record['run_commands']={key:[str(x) for x in cmd] for key,cmd in runs.items()}
            for tool,cmd in runs.items():
                _,trace=timed(cmd,work,tool+'-warmup');assert trace==expected,(size,tool,trace,expected)
                record[tool+'_runs']=[]
            for i in range(args.repeat):
                for tool in (['dsim','vcs'] if i%2==0 else ['vcs','dsim']):
                    stats,trace=timed(runs[tool],work,f'{tool}-run-{i}');assert trace==expected,(size,tool,trace,expected)
                    raw=(work/f'{tool}-run-{i}.time').read_text()
                    for label,key in [('User time (seconds)','user_seconds'),('System time (seconds)','system_seconds')]:stats[key]=float(re.search(re.escape(label)+r': ([0-9.]+)',raw)[1])
                    record[tool+'_runs'].append(stats)
            record['status']='PASS';save();print('PASS sequential feedback scale',size,flush=True)
    except Exception as e:report['failure']=str(e);raise
    finally:save()
if __name__=='__main__':main()
