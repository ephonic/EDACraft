#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
from cases import CASES,materialize,trace

def run(cmd,cwd,ok=True):
    p=subprocess.run([str(v) for v in cmd],cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    if ok:assert p.returncode==0,(cmd,p.stdout)
    return p

def main():
    compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True);results={}
    for name in CASES:
        w=out/name;w.mkdir(exist_ok=True);case=materialize(w,name)
        args=case['args'];cmd=[compiler,*args,'--emit-preprocessed','expanded.v','--emit-deps','deps.json','--emit-ir','ir.json','-o',w/'simv']
        p=run(cmd,w);(w/'compile.log').write_text(p.stdout);q=run([w/'simv'],w);(w/'run.log').write_text(q.stdout);assert trace(q.stdout)==case['expected'],(name,q.stdout)
        deps=json.loads((w/'deps.json').read_text());assert deps['schema']=='dsim.preprocessing.v1' and deps['lines']
        assert all(Path(d).exists() for d in deps['dependencies'])
        assert len(deps['lines'])==len((w/'expanded.v').read_text().splitlines())
        text=run([compiler,*args,'-E'],w).stdout;assert text==(w/'expanded.v').read_text()
        # Independent source plus independent tool; explicit equivalent flags for filelists.
        if shutil.which('iverilog') and not case.get('iv_skip'):
            iv=run(['iverilog','-g2012','-s','top','-o',w/'iv',*case.get('iv_args',args)],w,not case.get('iv_failure'))
            (w/'icarus-compile.log').write_text(iv.stdout)
            if case.get('iv_failure'):assert iv.returncode and case['iv_failure'] in iv.stdout,(name,iv.stdout)
            else:
                iv=run(['vvp',w/'iv'],w);(w/'icarus.log').write_text(iv.stdout);assert trace(iv.stdout)==case['expected'],(name,iv.stdout)
        results[name]=dict(status='PASS',trace=case['expected'],inputs_sha256={p:hashlib.sha256((w/p).read_bytes()).hexdigest() for p in case['files']},arguments=args)
        if case.get('iv_failure'):results[name]['icarus_difference']=case['iv_failure']
        print('PASS preprocess',name,flush=True)
    negatives={
      'undefined':('module top; reg q; initial q=`NO; endmodule','undefined macro'),
      'recursive':('`define A `A\nmodule top; reg q; initial q=`A; endmodule','macro expansion limit'),
      'mutual':('`define A `B\n`define B `A\nmodule top; reg q; initial q=`A; endmodule','macro expansion limit'),
      'include':('`include "absent.vh"\n','include file not found'),
      'include_recursive':('`include "input.v"\n','include nesting limit'),
      'endif':('`endif\n','unmatched'), 'else':('`else\n','unmatched'),
      'conditional':('`ifdef X\nmodule top; endmodule\n','unterminated conditional'),
      'duplicate_else':('`ifdef X\n`else\n`else\n`endif\n','branch after `else'),
      'elsif_after_else':('`ifdef X\n`else\n`elsif Y\n`endif\n','branch after `else'),
      'bad_if':('`ifdef\n','expected one macro name'),
      'zero_parameters':('`define ZERO() 1\n','at least one formal parameter'),
      'parameter':('`define F(a,a) a\n','duplicate macro parameter'),
      'name':('`define 7 value\n','expected macro name'),
      'arguments':('`define F(a,b) a+b\nmodule top; reg q; initial q=`F(1); endmodule','missing macro argument'),
      'too_many':('`define F(a) a\nmodule top; reg q; initial q=`F(1,2); endmodule','too many macro arguments'),
      'function':('`define F(a) a\nmodule top; reg q; initial q=`F; endmodule','requires arguments'),
      'delimiters':('`define F(a) a\nmodule top; reg q; initial q=`F({1)); endmodule','unbalanced macro'),
      'unterminated_call':('`define F(a) a\nmodule top; reg q; initial q=`F(1','unterminated macro argument'),
      'macroquote':('`define F(a) `"a\nmodule top; initial $display(`F(hi)); endmodule','unterminated macro quote'),
      'expanded_endif':('`define CLOSE `endif\nmodule top; `CLOSE endmodule','unmatched `endif'),
      'expanded_else':('`define BAD `ifdef A `else `else `endif\nmodule top; `BAD endmodule','branch after `else'),
      'expanded_if':('`define BAD `ifdef\nmodule top; `BAD endmodule','expected one macro name'),
      'expanded_open':('`define OPEN `ifdef A\n`OPEN\n','unterminated conditional'),
      'include_extra':('`include "x.vh" extra\n','one quoted filename'),
      'comment':('module top; /* bad','unterminated block comment'),
      'string':('module top; initial $display("bad); endmodule','unterminated string literal'),
      'paste':('module top; wire a``b; endmodule','outside a macro'),
      'unsupported':('`default_nettype none\nmodule top; endmodule','preprocessing directives'),
      'nul':('module top;\x00endmodule','NUL byte'),
    }
    for name,(source,expected) in negatives.items():
        w=out/('reject-'+name);w.mkdir(exist_ok=True);(w/'input.v').write_text(source)
        p=run([compiler,'input.v','-o','failed'],w,False);(w/'run.log').write_text(p.stdout)
        assert p.returncode and expected in p.stdout and not (w/'failed').exists(),(name,p.stdout)
        print('PASS preprocess reject',name,flush=True)
    # Filelist path behavior, dependency clobber protection (including symlinks), diagnostics.
    w=out/'protections';w.mkdir(exist_ok=True);(w/'header.vh').write_text('module top; reg [7:0] q[0:2][0:2]; initial q[0][0]=; endmodule\n');(w/'input.v').write_text('`include "header.vh"\n');(w/'recursive.f').write_text('-f recursive.f\n')
    for args,error in [(['-f','recursive.f'],'recursive filelist'),(['-F','missing.f'],'cannot read'),(['-D','1BAD','input.v'],'invalid command-line macro'),(['input.v','--emit-only'],'header.vh:1:'),(['-f'],'missing argument')]:
        p=run([compiler,*args],w,False);assert p.returncode and error in p.stdout,(args,p.stdout)
    (w/'header.vh').write_text('module top; endmodule\n');(w/'list.f').write_text('input.v\n')
    for target in ['input.v','header.vh','list.f']:
        before=(w/target).read_bytes()
        for option in ['-o','--emit-cpp','--emit-ir','--emit-preprocessed','--emit-deps']:
            p=run([compiler,'-f','list.f',option,target,'--emit-only'],w,False);assert p.returncode and 'overwrite an input' in p.stdout,(target,option,p.stdout);assert (w/target).read_bytes()==before
    alias=w/'alias.vh'
    if alias.exists() or alias.is_symlink():alias.unlink()
    alias.symlink_to('header.vh');p=run([compiler,'input.v','--emit-preprocessed','alias.vh'],w,False);assert p.returncode and 'overwrite an input' in p.stdout
    before=(w/'header.vh').read_bytes();hard=w/'hardlink.vh'
    if hard.exists():hard.unlink()
    os.link(w/'header.vh',hard);p=run([compiler,'input.v','--emit-preprocessed','hardlink.vh'],w,False);assert p.returncode and 'overwrite an input' in p.stdout and (w/'header.vh').read_bytes()==before
    (w/'header.vh').write_text('module top;\nreg q;\ninitial q=;\nendmodule\n')
    p=run([compiler,'input.v','--emit-only'],w,False);(w/'syntax-diagnostic.log').write_text(p.stdout);assert p.returncode and 'header.vh:3:' in p.stdout,p.stdout
    (w/'header.vh').write_text('`define BODY \\\n wire okay; // ignored \\\n wire also_okay;\nmodule top;\n `BODY\n initial bad=;\nendmodule\n')
    p=run([compiler,'input.v','--emit-only'],w,False);(w/'continued-diagnostic.log').write_text(p.stdout);assert p.returncode and 'header.vh:6:' in p.stdout,p.stdout
    print('PASS filelist recursion, paths, source diagnostics and dependency output protection',flush=True)
    for option in ['+libext+', '+libext+.v+', '+libext+.v++sv', '+libext+../bad', '-y']:
        p=run([compiler,option,'input.v','--emit-only'],w,False)
        assert p.returncode and ('+libext+' in p.stdout or 'unknown option -y' in p.stdout),(option,p.stdout)
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    (out/'summary.json').write_text(json.dumps(dict(status='PASS',models=len(results),rejections=len(negatives),source_map_and_protections='PASS'),indent=2)+'\n')
if __name__=='__main__':main()
