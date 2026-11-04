"""Named finite SVA sequences, lexical binding, sampling, cloning and transactions."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache_path=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
cache={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache_path.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations,timeline
def run(command,work,label,ok=True):
 p=subprocess.run(list(map(str,command)),cwd=work,text=True,capture_output=True,timeout=300)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==(0 if ok else 1),(label,p.returncode,p.stdout[-2000:],p.stderr[-2000:])
 return p.stdout
def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
expected=json.loads((fixtures/'expected.json').read_text())
report=dict(status='RUNNING',models={},captures=0,rollbacks=0,commits=0)
try:
 for name in (sys.argv[4:] or expected):
  wanted=expected[name]
  work=out/name;work.mkdir(exist_ok=True);reference=None
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,fixtures/(name+'.sv'),*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-compile')
   wave=work/(backend+'.vcd');wave.unlink(missing_ok=True)
   text=run([work/backend,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,backend+'-run')
   assert [x for x in text.splitlines() if x.startswith('TRACE')]==wanted,(name,backend,text,wanted)
   current=(text,stream(wave))
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete per-signal ordered streams')
   report['captures']+=1
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  cxx=cache.get('DSIM_MODEL_CXX',cache['CMAKE_CXX_COMPILER'])
  if Path(cxx).name=='clang++' and sys.platform=='darwin':cxx='c++'
  for accept in [False,True]:
   label='commit' if accept else 'rollback';cpp=work/(label+'.cpp')
   patch='''
s.run_until(16000);
bool accepted=s.predict_until(95000,[](Sim&){},[](const Sim&){return ACCEPT;},[](Sim&){});
if(accepted!=ACCEPT||s.prediction_stats.COUNTER!=1)throw std::runtime_error("named sequence transaction mismatch");
s.run();
'''.replace('ACCEPT',str(accept).lower()).replace('COUNTER','commits' if accept else 'rollbacks')
   cpp.write_text(code.replace('\ns.run();\n',patch))
   flags=['-fp-model=strict'] if Path(cxx).name in ['icpx','icpc'] else []
   run([cxx,'-std=c++17','-O2','-pthread',*flags,'-I'+cache['DSIM_ZSTD_INCLUDE'],cpp,cache['DSIM_ZSTD_LIBRARY'],'-o',work/label],work,label+'-compile')
   wave=work/(label+'.vcd');wave.unlink(missing_ok=True)
   text=run([work/label,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,label+'-run')
   assert (text,stream(wave))==reference,(name,label,'transaction state or wave')
   report['captures']+=1;report['commits' if accept else 'rollbacks']+=1
  ir=json.loads((work/'parallel.json').read_text())
  if name=='parallel':
   assert ir['parallel']['partitions']==2,ir['parallel']
   run([work/'parallel','--parallel-stats'],work,'parallel-stats')
   assert '"partitions":2' in (work/'parallel-stats.stderr').read_text()
   values=timeline(*read(work/'parallel.vcd'))
   # VCS also starts the negedge property on the time-zero X->0 clock
   # initialization, adding the early D=1 success at time 20 ns.
   for port,value in [('one',3),('two',1)]:assert values[('top',port)][2][-1][1]==(value,0),port
  report['models'][name]=dict(status='PASS',source_sha256=hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),trace=wanted,parallel_partitions=ir['parallel']['partitions'])
  print('PASS named sequences',name,flush=True)
 negatives={
  'group_depth':('('*129+'a ##0 a'+')'*129,'nesting exceeds 128 groups'),
  'group_zero':('(a ##1 a)[*0]','known integral constant in 1..256'),
  'group_variable':('(a ##1 a)[*d]','known integral constant in 1..256'),
  'group_negative':('(a ##1 a)[*-1]','known integral constant in 1..256'),
  'group_unknown':("(a ##1 a)[*32'bx]",'known integral constant in 1..256'),
  'group_range':('(a ##1 a)[*1:2]','syntax error'),
  'group_stage':('(a ##0 a)[*129]','256 stages'),
  'group_nested_stage':('((a ##0 a)[*128])[*2]','256 stages'),
  'group_span':('(a ##65536 a)[*2]','total delay'),
  'group_outer_span':('##65536 (a ##0 a)[*2]','total delay'),
  'group_mutation':('(a ##1 (d++))[*2]','pure integral expression'),
  'zero':('a[*0]','known integral constant in 1..256'),
  'negative':('a[*-1]','known integral constant in 1..256'),
  'variable':('a[*d]','known integral constant in 1..256'),
  'unknown':("a[*32'bx]",'known integral constant in 1..256'),
  'too_many':('a[*257]','known integral constant in 1..256'),
  'wide':("a[*130'h100000000000000000000]",'known integral constant in 1..256'),
  'stage_limit':('a[*256] ##1 a','256 stages'),
  'span_limit':('##65536 a[*2]','total delay'),
  'span_sum':('##65535 a[*2] ##1 a','total delay'),
  'count_text':('a[*"abc"]','known integral constant in 1..256'),
  'range':('a[*1:2]','syntax error'),
  'unbounded':('a[*1:$]','syntax error'),
  'star':('a[*]','syntax error'),
  'plus':('a[+]','syntax error'),
  'goto':('a[->2]','syntax error'),
  'nonconsecutive':('a[=2]','syntax error'),
  'mutation':('(d++)[*2]','pure integral expression'),
  'memory':('array[d][*2]','property expression'),
 }
 for name,(expression,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text('module top;reg clk,a,array[2];integer d=2;assert property(@(posedge clk) 1 |-> '+expression+');endmodule\n')
  dest=out/(name+'.cpp');dest.write_text('keep original output')
  run([compiler,source,'--emit-only','--emit-cpp',dest],out,name,False)
  assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text())
  assert dest.read_text()=='keep original output',name
 declaration_negatives={
  'self':('sequence s;s;endsequence','recursive sequence reference'),
  'mutual':('sequence s;t();endsequence sequence t;s();endsequence','recursive sequence reference'),
  'unknown_name':('sequence s;missing;endsequence','missing'),
  'unknown_call':('sequence s;missing();endsequence','missing'),
  'duplicate':('sequence s;a;endsequence sequence s;a;endsequence','duplicate sequence'),
  'variable_conflict':('logic s;sequence s;a;endsequence',None),
  'property_conflict':('sequence s;a;endsequence property s;@(posedge clk) a;endproperty','property conflicts with a sequence'),
  'boolean':('sequence s;a;endsequence assert property(@(posedge clk) (s && a));','standalone sequence term'),
  'procedural':('sequence s;a;endsequence initial if(s)d++;','standalone sequence term'),
  'actual_arguments':('sequence s;a;endsequence assert property(@(posedge clk) s(a));','actual arguments'),
  'clocked':('sequence s;@(posedge clk) a;endsequence','syntax error'),
  'formals':('sequence s(input bit x);x;endsequence','syntax error'),
  'reference_stages':('sequence s;a[*129];endsequence assert property(@(posedge clk) s ##0 s);','256 stages'),
  'reference_repeat_stages':('sequence s;a ##0 a;endsequence assert property(@(posedge clk) s[*129]);','256 stages'),
  'reference_span':('sequence s;a ##65536 a;endsequence assert property(@(posedge clk) 1 |=> s);','total delay'),
  'reference_depth':(' '.join('sequence s'+str(i)+';s'+str(i+1)+';endsequence' for i in range(128))+' sequence s128;a;endsequence','reference nesting exceeds 128'),
  'indexed':('sequence s;a;endsequence assert property(@(posedge clk) s[0]);',None),
  'indexed_call':('sequence s;a;endsequence assert property(@(posedge clk) s[0]());',None),
  'closing_label':('sequence s;a;endsequence:t','closing label does not match'),
  'function_conflict':('function bit s();return 1;endfunction sequence s;a;endsequence',None),
  'procedural_call':('sequence s;a;endsequence initial s();',None),
 }
 for name,(body,diagnostic) in declaration_negatives.items():
  source=out/('decl_'+name+'.sv');source.write_text('module top;reg clk,a;integer d;'+body+' endmodule\n')
  dest=out/('decl_'+name+'.cpp');dest.write_text('keep original output')
  run([compiler,source,'--emit-only','--emit-cpp',dest],out,'decl_'+name,False)
  error=(out/('decl_'+name+'.stderr')).read_text();assert error and (diagnostic is None or diagnostic in error),(name,error)
  assert dest.read_text()=='keep original output',name
 source=out/'package.sv';source.write_text('package p;sequence s;1;endsequence endpackage module top;endmodule\n')
 dest=out/'package.cpp';dest.write_text('keep original output')
 run([compiler,source,'--emit-only','--emit-cpp',dest],out,'package',False)
 assert 'unsupported package item' in (out/'package.stderr').read_text() and dest.read_text()=='keep original output'
 for name,expression in [('max_span','##65281 a[*256]'),('count_expression','a[* (2+1)]'),('whitespace','a[ \n * 2]'),('minimum','a[*1]'),('group_count','(a ##0 a)[*(2+1)]'),('group_max_span','##65281 (a[*2])[*128]'),('boolean_parens','((a && a)) ##0 (((a)))'),('nested','((a ##0 a)) ##0 ((a[*2])[*2])')]:
  source=out/(name+'.sv');source.write_text('module top;reg clk,a;assert property(@(posedge clk) 1 |-> '+expression+');endmodule\n')
  run([compiler,source,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name)
 for name,text in [('unused','sequence s;a ##1 a;endsequence'),('forward','assert property(@(posedge clk) t());sequence t;s;endsequence sequence s();a;endsequence:s'),('maximum_depth',' '.join('sequence s'+str(i)+';s'+str(i+1)+';endsequence' for i in range(127))+' sequence s127;a;endsequence assert property(@(posedge clk) s0);')]:
  source=out/('positive_'+name+'.sv');source.write_text('module top;reg clk,a;'+text+' endmodule\n')
  run([compiler,source,'--emit-only','--emit-cpp',out/('positive_'+name+'.cpp')],out,'positive_'+name)
 source=out/'keywords.v';source.write_text('module top;integer sequence=3,endsequence=4;initial $display("TRACE keywords %0d %0d",sequence,endsequence);endmodule\n')
 run([compiler,source,'--language','verilog','-o',out/'keywords'],out,'keywords-compile')
 assert run([out/'keywords'],out,'keywords-run')=='TRACE keywords 3 4\n'
 report.update(status='PASS',negative_cases=len(negatives)+len(declaration_negatives)+1,base_negative_cases=len(negatives),declaration_negative_cases=len(declaration_negatives)+1)
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
