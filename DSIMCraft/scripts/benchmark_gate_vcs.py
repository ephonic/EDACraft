#!/usr/bin/env python3
"""Separate Network parser/binder scaling from gate generation/compile/run cost."""
import argparse,hashlib,json,platform,re,statistics,subprocess
from pathlib import Path
from compare_vcs import ROOT,timed


def workload(size,cycles):
    net=['module dut(input a,output y);']
    for i in range(size):
        target='y' if i==size-1 else 'n'+str(i)
        previous='a' if i==0 else 'n'+str(i-1)
        if i<size-1: net.append(f'wire {target};')
        net.append(f'INV g{i}(.A({previous}),.Y({target}));')
    net+=['endmodule']
    tb=f'''module top;
reg a; reg [31:0] i,sum; wire y;
dut u(.a(a),.y(y));
initial begin
 a=0; sum=0; #1;
 for(i=0;i<32'd{cycles};i=i+32'd1) begin
  a=~a; #1; sum=sum+y;
 end
 $display("TRACE sum=%0d y=%b time=%0d",sum,y,$time); $finish;
end endmodule
'''
    # Even chain preserves the input. Odd chain complements it.
    ones=(cycles+1)//2 if size%2==0 else cycles//2
    final=(cycles%2)^(size%2)
    expected=[f'TRACE sum={ones} y={final} time={cycles+1}']
    return '\n'.join(net)+'\n',tb,expected


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dsim',type=Path,default=ROOT/'build/dsim')
    ap.add_argument('--output',type=Path,default=ROOT/'build/benchmark-gate')
    ap.add_argument('--parse-sizes',type=int,nargs='+',default=[100000,1000000])
    ap.add_argument('--sizes',type=int,nargs='+',default=[1000,10000,100000])
    ap.add_argument('--cycles',type=int,default=200)
    ap.add_argument('--repeat',type=int,default=3)
    ap.add_argument('--parse-only',action='store_true')
    args=ap.parse_args()
    if args.repeat<1 or args.cycles<1 or min(args.parse_sizes+args.sizes)<1: ap.error('sizes/cycles/repeat must be positive')
    out=args.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    report={'host':platform.node(),'platform':platform.platform(),
            'dsim_version':subprocess.check_output([args.dsim.resolve(),'--version'],text=True).strip(),
            'repeat':args.repeat,'cycles':args.cycles,'warmup_runs_per_tool':1,
            'cxx_version':subprocess.check_output(['c++','--version'],text=True),
            'native_flags':['-std=c++17','-O2'],'vcs_flags':['-full64','-sverilog','-top','top'],
            'parse':{},'simulation':{},
            'note':'Serial runs. Parser/binder measurements omit RTL, C++ generation/compile and simulation; their peak RSS includes the whole check process. Simulation uses regular inverter chains that VCS may collapse. This synthetic workload does not establish real-design performance. Shared host, affinity/frequency uncontrolled.'}
    if not args.parse_only: report['vcs_version']=subprocess.check_output(['vcs','-full64','-ID'],text=True,stderr=subprocess.STDOUT)
    lib=ROOT/'tests/gate/cells.lib'; models=ROOT/'tests/gate/cells.v'
    report['library_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [lib,models]}
    def save(): (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        for size in args.parse_sizes:
            work=out/f'parse-{size}'; work.mkdir(exist_ok=True)
            net,_,_=workload(size,1); path=work/'input.v'; path.write_text(net)
            record={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,'runs':[]}
            report['parse'][str(size)]=record
            for i in range(args.repeat):
                output=work/f'network-{i}.json'
                stats,_=timed([args.dsim.resolve(),'--gate-check','--gate-netlist',path,'--gate-top','dut','--liberty',lib,'--emit-ir',output],work,f'parse-bind-{i}')
                ir=json.loads(output.read_text())
                assert ir['instance_count']==size and ir['network_instance_count']==size+1
                assert ir['network_net_count']==size+1 and ir['model_count']==1 and ir['pin_count']==2*size
                stats.update(parse_seconds=ir['parse_seconds'],bind_seconds=ir['bind_seconds'])
                record['runs'].append(stats)
            record['status']='PASS'; save(); print('PASS parse/bind',size,flush=True)
        if args.parse_only: return
        for size in args.sizes:
            work=out/f'simulation-{size}'; work.mkdir(exist_ok=True)
            net,tb,expected=workload(size,args.cycles)
            source,testbench=work/'input.v',work/'tb.v'; source.write_text(net); testbench.write_text(tb)
            record={'netlist_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'tb_sha256':hashlib.sha256(testbench.read_bytes()).hexdigest(),'trace':expected}
            report['simulation'][str(size)]=record
            native,vcs=work/'dsim_simv',work/'vcs_simv'
            prefix=[args.dsim.resolve(),'--gate-netlist',source,'--gate-top','dut','--liberty',lib,testbench]
            generate=prefix+['--emit-only','--emit-cpp',work/'model.cpp']
            native_compile=['c++','-std=c++17','-O2',work/'model.cpp','-o',native]
            vcs_compile=['vcs','-full64','-sverilog','-top','top',source,testbench,models,'-o',vcs]
            record['commands']={k:[str(a) for a in cmd] for k,cmd in [('dsim_generate',generate),('native_compile',native_compile),('vcs_compile',vcs_compile)]}
            record['dsim_generate'],_=timed(generate,work,'dsim-generate')
            record['generated_bytes']=(work/'model.cpp').stat().st_size
            record['native_compile'],_=timed(native_compile,work,'native-compile')
            record['vcs_compile'],_=timed(vcs_compile,work,'vcs-compile')
            record['run_commands']={'dsim':[str(native),'--max-events',str(max(10000000,size*args.cycles*20))],'vcs':[str(vcs)]}
            for tool,cmd in record['run_commands'].items():
                _,trace=timed(cmd,work,tool+'-warmup'); assert trace==expected,(size,tool,trace,expected)
                record[tool+'_runs']=[]
            for i in range(args.repeat):
                order=['dsim','vcs'] if i%2==0 else ['vcs','dsim']
                for tool in order:
                    stats,trace=timed(record['run_commands'][tool],work,f'{tool}-run-{i}'); assert trace==expected,(size,tool,trace,expected)
                    raw=(work/f'{tool}-run-{i}.time').read_text()
                    for label,key in [('User time (seconds)','user_seconds'),('System time (seconds)','system_seconds')]:
                        stats[key]=float(re.search(re.escape(label)+r': ([0-9.]+)',raw)[1])
                    record[tool+'_runs'].append(stats)
            record['status']='PASS'; save(); print('PASS gate simulation',size,flush=True)
    except Exception as e:
        report['failure']=str(e); raise
    finally: save()
if __name__=='__main__': main()
