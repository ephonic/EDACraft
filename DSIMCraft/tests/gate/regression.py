#!/usr/bin/env python3
"""Independent gate parser, binding, and RTL-stimulated native simulation."""
from pathlib import Path
import json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent
CASES=('four_state','hierarchy','connections','wide_connections','wide_ports','wide_constants','wide_inputs','wide_aliases','wide_atomic','seq_edges','seq_latches','seq_async','seq_feedback','seq_pipeline','seq_regions')

def run(args,ok=True):
    p=subprocess.run([str(a) for a in args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=90)
    if ok and p.returncode: raise RuntimeError(f'{args}: {p.returncode}\n{p.stdout}')
    return p

def traces(text): return [s for s in text.splitlines() if s.startswith('TRACE ')]
def library(case): return ROOT/('sequential.lib' if case.startswith('seq_') else 'cells.lib')
def reference_models(case): return ROOT/('sequential.v' if case.startswith('seq_') else 'cells.v')
def command(compiler,case):
    return [compiler,'--gate-netlist',ROOT/(case+'.net.v'),'--gate-top','dut','--liberty',library(case),ROOT/(case+'.tb.v')]

def main():
    compiler=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2]).resolve(); out.mkdir(parents=True,exist_ok=True)
    run([sys.executable,ROOT/'generate_cases.py','--check'])
    run([sys.executable,ROOT/'generate_wide_cases.py','--check'])
    run([sys.executable,ROOT/'generate_sequential_cases.py','--check'])
    results={}
    for case in CASES:
        work=out/case; work.mkdir(exist_ok=True)
        expected=json.loads((ROOT/(case+'.expected.json')).read_text())
        compiled=run(command(compiler,case)+['--emit-ir',work/'ir.json','-o',work/'simv'])
        native=run([work/'simv'])
        (work/'compile.log').write_text(compiled.stdout); (work/'run.log').write_text(native.stdout)
        assert traces(native.stdout)==expected,(case,native.stdout,expected)
        ir=json.loads((work/'ir.json').read_text()); gate=ir['gate_design']
        assert gate['frontend']=='gate-network' and gate['instance_count']>0
        assert gate['model_count']<=10
        assert gate['sequential_instance_count']==(17 if case=='seq_pipeline' else 3 if case=='seq_regions' else 6 if case=='seq_async' else 2 if case.startswith('seq_') else 0)
        assert gate['sequential_state_bit_count']==2*gate['sequential_instance_count']
        counts=dict(zip(gate['models'],gate['model_wait_pin_count']))
        dependency=dict(zip(gate['models'],gate['model_output_input_dependent']))
        for model in gate['models']:
            if model.startswith(('DFF','LATCH')) or model in ('TFF','SRLATCH'):
                assert dependency[model]==(model=='DFFOUT'),(case,model,dependency[model])
        for name,count in {'DFFP':1,'DFFN':1,'DFFE':1,'DFFOUT':3,'TFF':2,'LATCHP':2,'LATCHN':2}.items():
            if name in counts:assert counts[name]==count,(case,name,counts[name])
        assert len(ir['gate_scopes'])==(2 if case in ('four_state','seq_pipeline') else 1)
        # RTL elaborates only the testbench and each DUT port stub, no leaf gates.
        assert len(ir['scopes'])==(3 if case in ('four_state','seq_pipeline') else 2)
        if shutil.which('iverilog'):
            run(['iverilog','-g2012','-s','top','-o',work/'iv',ROOT/(case+'.tb.v'),ROOT/(case+'.net.v'),reference_models(case)])
            iv=run(['vvp',work/'iv']); (work/'icarus.log').write_text(iv.stdout)
            iv_expected=ROOT/(case+'.icarus.json')
            assert traces(iv.stdout)==(json.loads(iv_expected.read_text()) if iv_expected.exists() else expected),(case,iv.stdout)
        results[case]={'status':'PASS','trace':expected}
        print('PASS gate',case,flush=True)
    negatives={
        'expression': ('module dut(input a,b,output y); assign y=a&b; endmodule', 'does not approximate expressions'),
        'unary': ('module dut(input a,output y); assign y=~a; endmodule','expected identifier'),
        'behavior': ('module dut(input a,output y); always @(a) y=a; endmodule','unsupported gate simulation construct'),
        'initial': ('module dut; initial begin end endmodule','expected'),
        'reg': ('module dut; reg a; endmodule','unsupported gate simulation construct'),
        'unbound': ('module dut(input a,output y); MISSING g(.A(a),.Y(y)); endmodule','unbound gate cell'),
        'bad_pin': ('module dut(input a,output y); INV g(.A(a),.NO(y)); endmodule','unknown pin'),
        'duplicate_pin': ('module dut(input a,output y); INV g(.A(a),.A(a),.Y(y)); endmodule','duplicate gate pin'),
        'duplicate_instance': ('module dut(input a,output y); INV g(.A(a),.Y(y)); INV g(.A(a),.Y(y)); endmodule','duplicate gate instance'),
        'duplicate_module': ('module dut; endmodule module dut; endmodule','duplicate module'),
        'missing_semi': ('module dut(input a,output y); INV g(.A(a),.Y(y)) endmodule','Expected'),
        'range': ('module dut(input [0:3] a,output y); endmodule','descending width'),
        'bit_range': ('module dut(input [3:0] a,output y); INV g(.A(a[4]),.Y(y)); endmodule','out-of-range bit'),
        'positional_unknown': ('module dut(input a,output y); INV g(a,y); endmodule','positional leaf'),
        'cast': ("module dut(input a,output y); assign y=1'(a); endmodule",'casts'),
        'timescale': ('`timescale 1ns/10ns\nmodule dut; endmodule','precision'),
        'delay': ('module dut(input a,output y); INV #1 g(.A(a),.Y(y)); endmodule','expected'),
        'reserved_name': ('module dut(input a,output y); INV tri0(.A(a),.Y(y)); endmodule','reserved keyword'),
        'literal_output': ("module dut(input a); INV g(.A(a),.Y(1'b0)); endmodule",'output cannot drive a constant'),
        'unknown_hier_port': ('module sub(input a,output y); assign y=a; endmodule module dut(input a,output y); sub u(.a(a),.bad(y)); endmodule','unknown hierarchical gate port'),
        'too_many_hier_ports': ('module sub(input a,output y); assign y=a; endmodule module dut(input a,output y); sub u(a,y,a); endmodule','too many positional gate ports'),
        'reversed_part': ('module dut(input [3:0] a,output y); INV g(.A(a[1:2]),.Y(y)); endmodule','part-select direction'),
        'empty_concat': ('module dut(input a,output y); INV g(.A({}),.Y(y)); endmodule','empty structural concatenation'),
        'zero_replication': ("module dut(output y); assign y={0{1'b1}}; endmodule",'zero-width'),
        'wide_replication': ("module dut(output y); assign y={1000000{2'b11}}; endmodule",'width exceeds'),
        'unsized_concat': ("module dut(output y); assign y={1,1'b1}; endmodule",'unsized constant'),
        'bad_literal': ("module dut(output y); assign y=4'b102; endmodule",'invalid structural based digit'),
        'zero_literal': ("module dut(output y); assign y=0'b1; endmodule",'literal width'),
        'signed_wire': ('module dut; wire signed [3:0] a; endmodule','reserved keyword'),
        'output_replication': ("module dut(input a,output y); assign {2{y}}={a,a}; endmodule",'output lvalue'),
        'constant_concat_output': ("module dut(input a,output y); INV g(.A(a),.Y({y,1'b0})); endmodule",'cannot drive a constant'),
        'inout_width': ('module sub(inout [1:0] a); endmodule module dut(inout a); sub u(a); endmodule','inout gate port width mismatch'),
        'reserved_generated': ('module dut; wire __dsim_pin_a; endmodule','reserved generated'),
        'escaped_bit_name': ('module dut; wire \\a[0] ; endmodule','distinct-name representation'),
        'recursive': ('module dut(input a,output y); dut g(a,y); endmodule','maximum hierarchy'),
    }
    for name,(source,message) in negatives.items():
        path=out/(name+'.v'); path.write_text(source)
        p=run([compiler,'--gate-check','--gate-netlist',path,'--gate-top','dut','--liberty',ROOT/'cells.lib'],ok=False)
        (out/(name+'.log')).write_text(p.stdout)
        assert p.returncode and message.lower() in p.stdout.lower(),(name,p.stdout)
        print('PASS gate reject',name,flush=True)
    library_negatives={
        'missing_function': 'pin(A) { direction : input; } pin(Y) { direction : output; }',
        'bad_function': 'pin(A) { direction : input; } pin(Y) { direction : output; function : "A ? A"; }',
        'unknown_function_pin': 'pin(A) { direction : input; } pin(Y) { direction : output; function : "MISSING"; }',
        'inout_cell': 'pin(A) { direction : input; } pin(Y) { direction : inout; function : "A"; }',
    }
    sequential_negatives={
        'ff_no_clock':'ff(IQ,IQN) { next_state : "A"; }',
        'ff_no_next':'ff(IQ,IQN) { clocked_on : "A"; }',
        'latch_no_data':'latch(IQ,IQN) { enable : "A"; }',
        'latch_no_enable':'latch(IQ,IQN) { data_in : "A"; }',
        'latch_empty':'latch(IQ,IQN) {}',
        'ff_dual_clock':'ff(IQ,IQN) { clocked_on : "A"; clocked_on_also : "A"; next_state : "A"; }',
        'latch_dual_enable':'latch(IQ,IQN) { enable : "A"; enable_also : "A"; data_in : "A"; }',
        'ff_mixed_latch':'ff(IQ,IQN) { clocked_on : "A"; next_state : "A"; data_in : "A"; }',
        'latch_mixed_ff':'latch(IQ,IQN) { enable : "A"; data_in : "A"; next_state : "A"; }',
        'ff_bad_state':'ff(A,IQN) { clocked_on : "A"; next_state : "A"; }',
        'ff_equal_states':'ff(IQ,IQ) { clocked_on : "A"; next_state : "A"; }',
        'ff_state_clock':'ff(IQ,IQN) { clocked_on : "IQ"; next_state : "A"; }',
        'ff_unknown_data':'ff(IQ,IQN) { clocked_on : "A"; next_state : "MISSING"; }',
        'ff_conflict_missing':'ff(IQ,IQN) { clocked_on : "A"; next_state : "A"; clear : "A"; preset : "A"; }',
        'ff_conflict_without_controls':'ff(IQ,IQN) { clocked_on : "A"; next_state : "A"; clear_preset_var1 : L; }',
        'ff_conflict_invalid':'ff(IQ,IQN) { clocked_on : "A"; next_state : "A"; clear : "A"; preset : "A"; clear_preset_var1 : K; }',
        'ff_duplicate_attribute':'ff(IQ,IQN) { clocked_on : "A"; next_state : "A"; next_state : "A"; }',
        'ff_multiple_groups':'ff(IQ,IQN) { clocked_on : "A"; next_state : "A"; } ff(JQ,JQN) { clocked_on : "A"; next_state : "A"; }',
        'ff_bank':'ff_bank(IQ,IQN,2) { clocked_on : "A"; next_state : "A"; }',
        'latch_bank':'latch_bank(IQ,IQN,2) { enable : "A"; data_in : "A"; }',
        'state_table':'statetable("A","IQ") { table : "0 : - : L"; }',
    }
    for name,body in sequential_negatives.items():
        library_negatives[name]=body+' pin(A) { direction : input; } pin(Y) { direction : output; function : "IQ"; }'
    net=out/'library-negative.v'; net.write_text('module dut(input a,output y); CELL g(.A(a),.Y(y)); endmodule')
    for name,body in library_negatives.items():
        lib=out/(name+'.lib'); lib.write_text('library(l) { cell(CELL) {'+body+'} }')
        p=run([compiler,'--gate-check','--gate-netlist',net,'--gate-top','dut','--liberty',lib],ok=False)
        (out/(name+'.log')).write_text(p.stdout)
        assert p.returncode,(name,p.stdout)
        print('PASS gate library reject',name,flush=True)
    # Continuous gate drivers remain sensitive during their own output update.
    # Reset first, then enable y=~y: the self-feedback must exhaust the budget.
    work=out/'self-feedback'; work.mkdir(exist_ok=True)
    lib=work/'cell.lib'; net=work/'net.v'; tb=work/'tb.v'
    lib.write_text('library(l) { cell(FB) { pin(A) { direction : input; } pin(B) { direction : input; } pin(Y) { direction : output; function : "A * B\'"; } } }')
    net.write_text('module dut(input a,output y); FB g(.A(a),.B(y),.Y(y)); endmodule')
    tb.write_text('module top; reg a; wire y; dut u(a,y); initial begin a=0; #1 a=1; #1 $finish; end endmodule')
    run([compiler,'--gate-netlist',net,'--gate-top','dut','--liberty',lib,tb,'-o',work/'simv'])
    p=run([work/'simv','--max-events','1000'],ok=False)
    (work/'run.log').write_text(p.stdout)
    assert p.returncode and 'event/instruction limit exceeded' in p.stdout,p.stdout
    print('PASS bounded gate self-feedback',flush=True)
    work=out/'latch-feedback'; work.mkdir(exist_ok=True)
    lib=work/'cell.lib'; net=work/'net.v'; tb=work/'tb.v'
    lib.write_text('library(l) { cell(FB) { latch(IQ,IQN) { enable : "G"; data_in : "IQ\'"; clear : "R"; } pin(G) { direction : input; } pin(R) { direction : input; } pin(Y) { direction : output; function : "IQ"; } } }')
    net.write_text('module dut(input g,r,output y); FB f(.G(g),.R(r),.Y(y)); endmodule')
    tb.write_text('module top; reg g,r; wire y; dut u(g,r,y); initial begin g=0;r=1;#1;r=0;g=1;#1;$finish;end endmodule')
    run([compiler,'--gate-netlist',net,'--gate-top','dut','--liberty',lib,tb,'-o',work/'simv'])
    p=run([work/'simv','--max-events','1000'],ok=False);(work/'run.log').write_text(p.stdout)
    assert p.returncode and 'event/instruction limit exceeded' in p.stdout,p.stdout
    print('PASS bounded latch self-feedback',flush=True)
    sys.path.insert(0,str(ROOT.parents[1]/'scripts'))
    from benchmark_gate_vcs import workload
    for size,cycles in [(1,1),(2,3),(17,5)]:
        net,tb,expected=workload(size,cycles)
        work=out/f'benchmark-smoke-{size}'; work.mkdir(exist_ok=True)
        source,testbench=work/'net.v',work/'tb.v'; source.write_text(net); testbench.write_text(tb)
        run([compiler,'--gate-netlist',source,'--gate-top','dut','--liberty',ROOT/'cells.lib',testbench,'-o',work/'simv'])
        assert traces(run([work/'simv']).stdout)==expected
        if shutil.which('iverilog'):
            run(['iverilog','-g2012','-s','top','-o',work/'iv',source,testbench,ROOT/'cells.v'])
            assert traces(run(['vvp',work/'iv']).stdout)==expected
        print('PASS gate benchmark checksum',size,cycles,flush=True)
    from benchmark_sequential_vcs import workload as sequential_workload
    for size,cycles in [(2,3),(17,9),(65,11)]:
        net,tb,expected,_=sequential_workload(size,cycles)
        work=out/f'sequential-benchmark-smoke-{size}'; work.mkdir(exist_ok=True)
        source,testbench=work/'net.v',work/'tb.v'; source.write_text(net); testbench.write_text(tb)
        run([compiler,'--gate-netlist',source,'--gate-top','dut','--liberty',ROOT/'cells.lib','--liberty',ROOT/'sequential.lib',testbench,'-o',work/'simv'])
        actual=traces(run([work/'simv']).stdout);assert actual==expected,(size,actual,expected)
        if shutil.which('iverilog'):
            run(['iverilog','-g2012','-s','top','-o',work/'iv',source,testbench,ROOT/'cells.v',ROOT/'sequential.v'])
            assert traces(run(['vvp',work/'iv']).stdout)==expected
        print('PASS sequential feedback benchmark checksum',size,cycles,flush=True)
    # A clock function depends on E even when the direct C input is unchanged.
    work=out/'gated-clock';work.mkdir(exist_ok=True)
    (work/'cell.lib').write_text('library(l) { cell(CELL) { ff(IQ,IQN) { clocked_on : "C & E"; next_state : "D"; } pin(C) { direction : input; } pin(D) { direction : input; } pin(E) { direction : input; } pin(Q) { direction : output; function : "IQ"; } } }')
    (work/'net.v').write_text('module dut(input c,d,e,output y); CELL g(.C(c),.D(d),.E(e),.Q(y)); endmodule')
    (work/'cell.v').write_text('module CELL(input C,D,E,output Q); wire clk; assign clk=C&E; DFFP f(.C(clk),.D(D),.Q(Q)); endmodule')
    steps=["c=0;d=0;e=0;#1;","c=1;#1;","e=1;#1;","e=0;#1;d=1;#1;e=1;#1;","d=0;#1;","c=1'bx;#1;","c=0;#1;c=1'bx;#1;","e=0;#1;c=1;#1;d=1;#1;e=1;#1;"]
    expected=[];body=['module top; reg c,d,e; wire y; dut u(c,d,e,y); initial begin']
    for i,(step,value) in enumerate(zip(steps,'xx0111x1')):
        body += [step,f'$display("TRACE i=%0d y=%b",{i},y);'];expected.append(f'TRACE i={i} y={value}')
    (work/'tb.v').write_text('\n'.join(body+['$finish;end endmodule'])+'\n')
    (work/'expected.json').write_text(json.dumps(expected,indent=2)+'\n')
    run([compiler,'--gate-netlist',work/'net.v','--gate-top','dut','--liberty',work/'cell.lib',work/'tb.v','-o',work/'simv'])
    actual=run([work/'simv']);(work/'run.log').write_text(actual.stdout);assert traces(actual.stdout)==expected
    if shutil.which('iverilog'):
        run(['iverilog','-g2012','-s','top','-o',work/'iv',work/'net.v',work/'tb.v',work/'cell.v',ROOT/'sequential.v'])
        actual=run(['vvp',work/'iv']);(work/'icarus.log').write_text(actual.stdout);assert traces(actual.stdout)==expected
    print('PASS gated clock expression dependencies',flush=True)
    # Protect the structural and Liberty inputs against all output paths too.
    for path in [ROOT/'cells.lib',ROOT/'four_state.net.v']:
        before=path.read_bytes()
        p=run(command(compiler,'four_state')+['--emit-ir',path],ok=False)
        assert p.returncode and 'overwrite an input' in p.stdout and path.read_bytes()==before
    p=run(command(compiler,'four_state')+[ROOT/'four_state.net.v'],ok=False)
    assert p.returncode and 'must not also be passed as an RTL source' in p.stdout
    print('PASS gate input path protection',flush=True)
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
if __name__=='__main__': main()
