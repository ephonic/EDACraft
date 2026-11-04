#!/usr/bin/env python3
"""Same-host native off/VCD/DWF costs and common top-level VCS VCD comparison."""
import argparse,hashlib,json,platform,re,statistics,struct,subprocess,sys
from pathlib import Path
from benchmark_sequential_vcs import workload
from compare_vcs import timed,ROOT
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,bit_timeline,dwf


def wave_digest(path):
    with path.open('rb' if path.suffix=='.dwf' else 'r') as f:
        if path.suffix=='.dwf':
            r=dwf.Reader(f);m,events=r.meta,r.events()
        else:m,stream=dwf.read_vcd_header(f);events=dwf.vcd_events(stream,m)
        digest=hashlib.sha256();count=0
        for t,k,p in events:
            digest.update(struct.pack('<Q',t));digest.update(k.encode()+b'\0')
            if k=='value':
                ident,(a,b)=p;s=m['signals'][ident];digest.update(s['code'].encode()+b'\0');digest.update(struct.pack('<QQ',a,b))
            elif k=='control':digest.update(json.dumps(p,separators=(',',':')).encode())
            count+=1
        return dict(events=count,event_sha256=digest.hexdigest(),header_sha256=hashlib.sha256(json.dumps(m['header']).encode()).hexdigest(),signals=len(m['signals']))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dsim',type=Path,default=ROOT/'build/dsim');ap.add_argument('--output',type=Path,default=ROOT/'build/benchmark-waveform')
    ap.add_argument('--sizes',type=int,nargs='+',default=[1000,10000]);ap.add_argument('--cycles',type=int,default=200);ap.add_argument('--repeat',type=int,default=3);a=ap.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    report=dict(host=platform.node(),dsim_version=subprocess.check_output([a.dsim,'--version'],text=True).strip(),repeat=a.repeat,cycles=a.cycles,warmups=1,cases={},
       note='Nonuniform XOR/DFF feedback. Own run variants serial and measured in rotating order after one warmup each. Native all-net VCD/DWF have identical signal range and capture=settled. VCS VCD selects depth 1 at top only; compare with native_top_vcd, not all-net file sizes. Shared host/normal buffered filesystem; CPU affinity and fsync uncontrolled; no timing/foundry/FST equivalence.')
    libs=[ROOT/'tests/gate/cells.lib',ROOT/'tests/gate/sequential.lib'];models=[ROOT/'tests/gate/cells.v',ROOT/'tests/gate/sequential.v']
    report['libraries_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in libs+models}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        for size in a.sizes:
            w=out/f'size-{size}';w.mkdir(exist_ok=True);net,tb,expected,metadata=workload(size,a.cycles)
            (w/'input.v').write_text(net);(w/'tb.v').write_text(tb)
            (w/'dump.v').write_text('module capture;initial if($test$plusargs("dump")) begin $dumpfile("vcs.vcd");$dumpvars(1,top);end endmodule\n')
            row=dict(trace=expected,workload=metadata,inputs_sha256={p:hashlib.sha256((w/p).read_bytes()).hexdigest() for p in ['input.v','tb.v','dump.v']},commands={},runs={})
            report['cases'][str(size)]=row;save()
            base=[a.dsim.resolve(),'--gate-netlist','input.v','--gate-top','dut','tb.v']
            for lib in libs:base+=['--liberty',lib]
            commands={'compile_plain':[*base,'-o',w/'plain'],'compile_instrumented':[*base,'--wave-support','-o',w/'native'],
                      'compile_vcs':['vcs','-full64','-sverilog','-top','top','-top','capture','input.v','tb.v','dump.v',*models,'-o',w/'vcs']}
            for key,cmd in commands.items():
                row['commands'][key]=[str(x) for x in cmd];row[key],_=timed(cmd,w,key,timeout=900)
            limit=str(max(10000000,size*a.cycles*100))
            variants={'plain':[w/'plain','--max-events',limit], 'native_disabled':[w/'native','--max-events',limit],
                'native_vcd':[w/'native','--max-events',limit,'--waveform',w/'native.vcd','--wave-format','vcd','--wave-mode','settled','--wave-timescale','1s','--wave-stats'],
                'native_dwf':[w/'native','--max-events',limit,'--waveform',w/'native.dwf','--wave-mode','settled','--wave-timescale','1s','--wave-stats'],
                'native_top_vcd':[w/'native','--max-events',limit,'--waveform',w/'top.vcd','--wave-format','vcd','--wave-mode','settled','--wave-scope','top','--wave-depth','1','--wave-timescale','1s','--wave-stats'],
                'vcs_disabled':[w/'vcs'], 'vcs_vcd':[w/'vcs','+dump']}
            files={'native_vcd':w/'native.vcd','native_dwf':w/'native.dwf','native_top_vcd':w/'top.vcd','vcs_vcd':w/'vcs.vcd'}
            row['run_commands']={key:[str(x) for x in cmd] for key,cmd in variants.items()}
            def execute(key,stem):
                if key in files:files[key].unlink(missing_ok=True)
                stats,trace=timed(variants[key],w,stem,timeout=600);assert trace==expected,(size,key,trace,expected)
                raw=(w/(stem+'.time')).read_text()
                stats['cpu_seconds']=sum(float(re.search(re.escape(label)+r': ([0-9.]+)',raw)[1]) for label in ['User time (seconds)','System time (seconds)'])
                if key in files:
                    dest=w/(stem+files[key].suffix);files[key].rename(dest)
                    stats['wave_bytes']=dest.stat().st_size;stats['wave_file']=dest.name
                    stats['wave_sha256']=hashlib.sha256(dest.read_bytes()).hexdigest()
                    log=(w/(stem+'.log')).read_text();match=re.search(r'WAVE (\{.*\})',log)
                    if match:stats['capture_stats']=json.loads(match[1])
                return stats
            for key in variants:execute(key,key+'-warmup');row['runs'][key]=[]
            keys=list(variants)
            for i in range(a.repeat):
                for key in keys[i:]+keys[:i]:
                    row['runs'][key].append(execute(key,f'{key}-run-{i}'));save()
            # All native runs are deterministic; compare complete all-net ordered
            # event streams across formats outside the timed simulation sections.
            for key in ['native_vcd','native_dwf']:
                runs=row['runs'][key]
                assert len({r['wave_sha256'] for r in runs})==1
                row[key+'_decoded']=wave_digest(w/runs[-1]['wave_file'])
            assert row['native_vcd_decoded']==row['native_dwf_decoded']
            x=read(w/row['runs']['native_top_vcd'][-1]['wave_file']);y=read(w/row['runs']['vcs_vcd'][-1]['wave_file'])
            assert bit_timeline(*x)==bit_timeline(*y),(size,'top-level waveform mismatch')
            row['medians']={key:{'cpu_seconds':statistics.median(r['cpu_seconds'] for r in runs),'wall_seconds':statistics.median(r['wall_seconds'] for r in runs),
                                'rss_kb':statistics.median(r['peak_rss_kb'] for r in runs),**({'wave_bytes':runs[-1]['wave_bytes']} if key in files else {})} for key,runs in row['runs'].items()}
            row['status']='PASS';save();print('PASS native waveform costs / common top VCS',size,flush=True)
    except Exception as e:report['failure']=str(e);raise
    finally:save()


if __name__=='__main__':main()
