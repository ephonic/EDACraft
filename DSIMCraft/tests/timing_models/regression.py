from pathlib import Path
import hashlib, json, subprocess, sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
compiler=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
records={}
def run(name,args,ok=True,message=None):
    p=subprocess.run([str(compiler),*[str(a) for a in args]],capture_output=True,text=True,timeout=120)
    (out/(name+'.stdout')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
    assert (p.returncode==0)==ok,(name,p.stdout,p.stderr)
    if message:assert message in p.stderr,(name,p.stderr,message)
    if not ok:assert not p.stdout,(name,p.stdout)
    records[name]=dict(returncode=p.returncode,stdout_sha256=hashlib.sha256(p.stdout.encode()).hexdigest(),stderr=p.stderr)
    return json.loads(p.stdout) if ok else p

metadata=run('metadata',['--timing-model-check',HERE/'models.v','--emit-ir',out/'metadata.json'])
assert metadata['functional_verilog_compiled'] is False
c,f=metadata['models'];assert c['name']=='C' and c['precision_fs']==10000 and f['precision_fs']==1000
assert len(c['paths'])==4 and len(c['checks'])==4 and len(f['checks'])==2
assert c['paths'][3]['output_polarity']=='+' and c['paths'][2]['ifnone']
base=['--sdf-bind-check',HERE/'delay.sdf','--gate-netlist',HERE/'net.v','--gate-top','dut','--liberty',HERE/'cells.lib','--sdf-tick','1ps','--gate-models',HERE/'models.v']
tables=run('tables',base)
assert not tables['runtime_annotation'] and tables['path_updates']==8 and tables['distinct_paths']==7
assert [r['ticks'][:2] for r in tables['paths']]==[[60,50],[70,80],[90,90],[100,100],[110,120],[110,120],[20,20]]
min_sdf=run('independent-sdf-corner',base+['--sdf-corner','min'])
min_model=run('independent-model-corner',base+['--sdf-corner','min','--gate-model-corner','min'])
assert min_sdf['paths'][-1]['ticks'][:2]==[20,20]
assert min_model['paths'][-1]['ticks'][:2]==[10,20]

# All previous VCS numeric references now obtain scale/base from an actual
# preprocessed specify model. Compare the complete 12-transition table via
# the same separated input trace; this is table verification, not a CLI run.
numeric=ROOT/'tests/sdf_path';values=[0,1,3,2,0,2,1,2,3,0,3,1,0]
numeric_net=out/'numeric-net.v';numeric_net.write_text('module dut(input A,output Z); B u(.A(A),.Z(Z)); endmodule\n')
numeric_lib=out/'numeric.lib';numeric_lib.write_text((numeric/'buffer.lib').read_text().replace('cell(BUF)','cell(B)'))
transition={(0,1):0,(1,0):1,(0,3):2,(3,1):3,(1,3):4,(3,0):5,
            (0,2):6,(2,1):7,(1,2):8,(2,0):9,(2,3):10,(3,2):11}
supported=rejected=0
for row in json.loads((numeric/'oracles.json').read_text())['cases']:
    model=out/(row['name']+'.v');model.write_text('`timescale '+row['scale']+'\nmodule B(input A,output Z); assign Z=A; specify (A=>Z)=('+row['base']+'); endspecify endmodule\n')
    original=(numeric/row['sdf']).read_bytes();assert hashlib.sha256(original).hexdigest()==row['input_sha256']
    sdf=out/(row['name']+'.sdf');sdf.write_text(original.decode().replace('(INSTANCE)','(INSTANCE u)'))
    args=['--sdf-bind-check',sdf,'--gate-netlist',numeric_net,'--gate-top','dut','--liberty',numeric_lib,'--sdf-tick','1ps','--gate-models',model]
    if row.get('unsupported'):
        run(row['name'],args,False,'unsupported VCS readback');rejected+=1;continue
    r=run(row['name'],args);assert len(r['paths'])==1,row['name'];ticks=r['paths'][0]['ticks']
    trace=[];previous=2
    for i,value in enumerate(values):
        time=1000+100*i+ticks[transition[previous,value]];previous=value
        trace.append(f'TRACE t={time} z={str(value) if value<2 else "x" if value==2 else "z"}')
    assert trace==row['expected'],(row['name'],trace,row['expected']);supported+=1
assert (supported,rejected)==(54,4)

# Late error: report output remains untouched; no partially matched table.
bad=out/'bad.sdf';report=out/'protected.json';report.write_text('keep-report')
source=(HERE/'delay.sdf').read_text();bad.write_text(source.replace('(IOPATH B Y (0.071) (0.081))',"(COND A==1'b1 (IOPATH B Y (0.071) (0.081)))"))
args=base.copy();args[1]=bad
run('late-unmatched',args+['--emit-ir',report],False,'no exact model path')
assert report.read_text()=='keep-report'

negative={
 'missing-semi':('module C(input A,output Z); specify (A=>Z)=0 endspecify endmodule','missing semicolon'),
 'wrong-direction':('module C(input A,output Z); specify (Z=>A)=0; endspecify endmodule','path source'),
 'duplicate-model':('module C(); endmodule module C(); endmodule','duplicate model'),
 'unknown-specify':('module C(); specify nonsense; endspecify endmodule','unsupported specify'),
 'bad-check':('module C(); specify $unknown(1,2,3); endspecify endmodule','unknown timing check'),
 'short-check':('module C(); specify $setup(A,1); endspecify endmodule','too few'),
 'empty-check':('module C(); specify $setup(A,,1); endspecify endmodule','empty required'),
 'parameterized':('module C #(parameter T=0)(input A,output Z); endmodule','instance specialization'),
 'generate':('module C(); generate endgenerate endmodule','needs elaboration'),
 'truncated':('module C(input A,output Z); specify (A=>Z)=0;','unterminated specify'),
 'delay-count':('module C(input A,output Z); specify (A=>Z)=(1,2,3,4); endspecify endmodule','1,2,3,6 or 12'),
 'header-port':('module C(A,Z); input A; endmodule','undeclared header'),
 'extra-port':('module C(A); input A; output Z; endmodule','absent from header'),
 'parallel-list':('module C(input A,B,output Z); specify (A,B=>Z)=0; endspecify endmodule','parallel path'),
}
for name,(source,message) in negative.items():
    path=out/(name+'.v');path.write_text(source)
    run(name,['--timing-model-check',path,'--emit-ir',report],False,message)
    assert report.read_text()=='keep-report'

for name,expression,message in [('cycle','specparam a=b,b=a; (A=>Z)=a;','cyclic'),
                                ('unknown','(A=>Z)=missing;','unknown model constant'),
                                ('arithmetic','(A=>Z)=1+2;','unsupported model delay'),
                                ('overflow','(A=>Z)=1e80;','overflow')]:
    model=out/(name+'.v');model.write_text('`timescale 1ns/1ps\nmodule B(input A,output Z); specify '+expression+' endspecify endmodule\n')
    args=['--sdf-bind-check',out/'primary_tiny-increment.sdf','--gate-netlist',numeric_net,'--gate-top','dut','--liberty',numeric_lib,'--sdf-tick','1ps','--gate-models',model,'--emit-ir',report]
    run(name,args,False,message);assert report.read_text()=='keep-report'

# Included dependencies are protected too, and model preprocessor directives
# retain source locations and independent module precision.
included=out/'ports.vh';included.write_text('input A; output Z;\n')
model=out/'included.v';model.write_text('`timescale 1ns/1ps\nmodule B(A,Z);\n`include "ports.vh"\nspecify (A=>Z)=0; endspecify endmodule\n')
data=run('include',['--timing-model-check','-I',out,model]);assert str(included) in data['dependencies']
before=included.read_bytes()
run('overwrite-include',['--timing-model-check','-I',out,model,'--emit-ir',included],False,'overwrite an input')
assert included.read_bytes()==before
run('codegen-models',['--gate-models',model,numeric/'buffer.v'],False,'requires --sdf-bind-check')

# New independent VCS probes show an omitted edge on EITHER side matches an
# explicitly edged path; two explicitly different edges do not match.
for name,model_edge,sdf_edge,matched in [
    ('unspecified-to-posedge','posedge A','A',True),
    ('posedge-to-unspecified','A','(posedge A)',True),
    ('posedge-to-posedge','posedge A','(posedge A)',True),
    ('negedge-to-posedge','posedge A','(negedge A)',False)]:
    model=out/(name+'.v');path='(A=>Z)' if model_edge=='A' else '('+model_edge+' => (Z:A))'
    model.write_text('`timescale 1ns/1ps\nmodule B(input A,output Z); specify '+path+'=(0.001,0.002); endspecify endmodule\n')
    sdf=out/(name+'.sdf');sdf.write_text('(DELAYFILE (SDFVERSION "3.0") (TIMESCALE 1ns) (CELL (CELLTYPE "B") (INSTANCE u) (DELAY (ABSOLUTE (IOPATH '+sdf_edge+' Z (0.017) (0.023))))))\n')
    args=['--sdf-bind-check',sdf,'--gate-netlist',numeric_net,'--gate-top','dut','--liberty',numeric_lib,'--sdf-tick','1ps','--gate-models',model]
    data=run(name,args,matched,None if matched else 'no exact model path')
    if matched:assert len(data['paths'])==1 and data['paths'][0]['ticks'][:2]==[17,23]

summary=dict(status='PASS',compiler_sha256=hashlib.sha256(compiler.read_bytes()).hexdigest(),
             supported_previous_vcs_tables=supported,known_unsupported_rejections=rejected,
             cli_cases=records,scope='Specify metadata and model-matched numeric tables. No general runtime SDF annotation claim.')
(out/'results.json').write_text(json.dumps(summary,indent=2)+'\n')
print('PASS specify metadata/full-path isolation, 54 VCS-derived tables, 4 known rejections, strict errors and input protection')
