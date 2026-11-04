#!/usr/bin/env python3
"""Exhaust Liberty inversion syntax, precedence and tri-state controls in 4 states."""
from pathlib import Path
import argparse,itertools,json,shutil,subprocess


def fixture():
    # Independent scalar truth tables: inversion of Z produces X, not Z.
    invert=dict(zip('01xz','10xx'))
    def both(a,b): return '0' if '0' in (a,b) else '1' if a==b=='1' else 'x'
    def either(a,b): return '1' if '1' in (a,b) else '0' if a==b=='0' else 'x'
    def xor(a,b): return 'x' if a in 'xz' or b in 'xz' else str(int(a)^int(b))
    functions=[
        ('!A','~A',lambda a,b,c:invert[a]),
        ("A'",'~A',lambda a,b,c:invert[a]),
        ('!!A','~(~A)',lambda a,b,c:invert[invert[a]]),
        ("A''",'~(~A)',lambda a,b,c:invert[invert[a]]),
        ("(!A)'",'~(~A)',lambda a,b,c:invert[invert[a]]),
        ("!(A B')",'~(A & ~B)',lambda a,b,c:invert[both(a,invert[b])]),
        ("(A ^ B)'",'~(A ^ B)',lambda a,b,c:invert[xor(a,b)]),
        ("!A B + C'",'(~A & B) | ~C',lambda a,b,c:either(both(invert[a],b),invert[c])),
        ("(A B ^ C)'",'~(A & (B ^ C))',lambda a,b,c:invert[both(a,xor(b,c))]),
        ("!(A + !B)",'~(A | ~B)',lambda a,b,c:invert[either(a,invert[b])]),
    ]
    pins=''.join(f'pin({p}) {{ direction : input; }}' for p in 'ABCE')
    pins+=''.join(f'pin(Y{i}) {{ direction : output; function : "{fn}"; }}' for i,(fn,_,_) in enumerate(functions))
    pins+='pin(T) { direction : output; function : "!A"; three_state : "!E"; }'
    lib='library(l) { cell(EXPRESSIONS) {'+pins+'} }\n'
    outputs=[f'y{i}' for i in range(len(functions))]+['t']
    net='module dut(input a,b,c,e,output '+','.join(outputs)+'); EXPRESSIONS g(.A(a),.B(b),.C(c),.E(e),'+','.join(f'.Y{i}(y{i})' for i in range(len(functions)))+',.T(t)); endmodule\n'
    models='module EXPRESSIONS(input A,B,C,E,output '+','.join(f'Y{i}' for i in range(len(functions)))+',T);\n'
    models+=''.join(f'assign Y{i}={v};\n' for i,(_,v,_) in enumerate(functions))
    models+="assign T=E?~A:1'bz; endmodule\n"
    tb=['module top; reg a,b,c,e; wire '+','.join(outputs)+'; dut u(a,b,c,e,'+','.join(outputs)+'); initial begin']
    expected=[]
    for index,(a,b,c,e) in enumerate(itertools.product('01xz',repeat=4)):
        tb += [f"a=1'b{a};b=1'b{b};c=1'b{c};e=1'b{e};#1;",f'$display("TRACE i={index} y=%b",{{'+','.join(outputs)+'});']
        t='z' if e=='0' else invert[a] if e=='1' else 'x'
        expected.append(f'TRACE i={index} y='+''.join(f(a,b,c) for _,_,f in functions)+t)
    tb+=['$finish;end endmodule']
    return {'cells.lib':lib,'net.v':net,'cells.v':models,'tb.v':'\n'.join(tb)+'\n'},expected


def main():
    ap=argparse.ArgumentParser();ap.add_argument('compiler',type=Path);ap.add_argument('out',type=Path);ap.add_argument('--vcs',action='store_true');args=ap.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    sources,expected=fixture()
    for name,text in sources.items():(out/name).write_text(text)
    (out/'expected.json').write_text(json.dumps(expected,indent=2)+'\n')
    def run(cmd,name):
        proc=subprocess.run(list(map(str,cmd)),cwd=out,text=True,capture_output=True,timeout=180)
        (out/(name+'.log')).write_text(proc.stdout+proc.stderr)
        assert proc.returncode==0,(name,proc.stdout,proc.stderr)
        return [line for line in proc.stdout.splitlines() if line.startswith('TRACE ')]
    run([args.compiler.resolve(),'--gate-netlist',out/'net.v','--gate-top','dut','--liberty',out/'cells.lib',out/'tb.v','--emit-cpp',out/'model.cpp','-o',out/'native'],'native-compile')
    assert run([out/'native'],'native-run')==expected
    tools=['native']
    if shutil.which('iverilog'):
        run(['iverilog','-g2012','-s','top','-o',out/'iv',out/'cells.v',out/'net.v',out/'tb.v'],'icarus-compile')
        assert run(['vvp',out/'iv'],'icarus-run')==expected;tools.append('icarus')
    if args.vcs:
        run(['vcs','-full64','-sverilog','-top','top',out/'cells.v',out/'net.v',out/'tb.v','-o',out/'vcs'],'vcs-compile')
        for i in range(3):assert run([out/'vcs'],f'vcs-run-{i}')==expected
        tools.append('vcs-three-runs')
    (out/'results.json').write_text(json.dumps(dict(status='PASS',patterns=len(expected),outputs=11,tools=tools),indent=2)+'\n')
    print('PASS 256 Liberty inversion/precedence/tri-state four-state patterns',tools,flush=True)


if __name__=='__main__':main()
