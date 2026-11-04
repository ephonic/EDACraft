from pathlib import Path
p=Path('tests/sequence_antecedents')
a=[1,1,0,1,1,1,1,0,'x','z',1,1,1,0,1,1]
b=[1,1,1,0,1,1,1,1,1,1,0,1,1,1,1,1]
c=[1,0,1,1,0,1,1,1,1,1,1,0,1,1,0,1]
d=[1,1,0,1,1,1,0,1,1,1,1,1,1,0,1,1]
assign=lambda i:'{a,b,c,d}=4\'b'+''.join(str(v[i]) for v in [a,b,c,d])+';'
(p/'basic.sv').write_text('''`timescale 1ns/1ps
module top;
reg clk=0,a=1,b=1,c=1,d=1;
integer tick=0,op=0,of=0,np=0,nf=0,rp=0,rf=0,covered=0,sp=0,sf=0;
always #5 clk=~clk;
assert property(@(posedge clk) a ##1 b |-> c) op++;else of++;
assume property(@(posedge clk) pair() |=> c) np++;else nf++;
assert property(@(posedge clk) (a ##0 b)[*2] |-> c ##1 d) rp++;else rf++;
cover property(@(posedge clk) pair |-> c) covered++;
assert property(@(posedge clk) a |-> c) sp++;else sf++;
sequence pair; a ##1 b;endsequence
initial begin
'''+assign(0)+'''\nrepeat(16)begin
#7;$display("TRACE antecedent %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",tick,op,of,np,nf,rp,rf,covered,sp,sf);
#3;tick++;case(tick)
'''+ '\n'.join(str(i)+':'+assign(i) for i in range(1,16))+'''\ndefault:a=0;endcase
end
#1;$finish;end
endmodule
''')
# Independent endpoint oracle: project each source start directly onto the known
# sample vector. No runtime attempt queue, dispatcher or generated code reused.
from collections import Counter
at=[Counter() for _ in a]
for start in range(len(a)):
 if a[start]==1:
  at[start]['sp' if c[start]==1 else 'sf']+=1
 if start+1<len(a) and a[start]==1 and b[start+1]==1:
  end=start+1;at[end]['op' if c[end]==1 else 'of']+=1
  if c[end]==1:at[end]['covered']+=1
  if end+1<len(a):at[end+1]['np' if c[end+1]==1 else 'nf']+=1
 if start+1<len(a) and a[start]==b[start]==a[start+1]==b[start+1]==1:
  end=start+1
  if c[end]!=1:at[end]['rf']+=1
  elif end+1<len(a):at[end+1]['rp' if d[end+1]==1 else 'rf']+=1
counts=Counter();expected=[]
for i,row in enumerate(at):
 counts.update(row);expected.append('TRACE antecedent '+str(i)+' '+' '.join(str(counts[x]) for x in ['op','of','np','nf','rp','rf','covered','sp','sf']))
import json
(p/'basic-independent.json').write_text(json.dumps(expected,indent=2)+'\n')
s=Path('tests/named_sequences/sampled.sv').read_text().replace('req |-> history[*3]','req ##1 history |-> history[*2]').replace('req |=> snapshot()[*2]','(req ##0 change)[*2] |=> snapshot()[*2]').replace('req |-> change[*2]','($rose(req) ##1 change) |-> $past(data) ##0 $sampled(data)')
(p/'sampled.sv').write_text(s.replace('sampled-named-seq','sampled-antecedent'))
s=Path('tests/named_sequences/clones.sv').read_text().replace('value[0] |-> pair()','pair() |-> value[0]').replace('value[0] |-> bridge','bridge |-> value[0]').replace('value[N] |=> ##(N-1) finish_pair()','finish_pair() |=> ##(N-1) pair')
(p/'clones.sv').write_text(s.replace('named-seq-clones','antecedent-clones'))
(p/'boundary.sv').write_text('''`timescale 1ns/1ps
module top;
reg clk=0,req=1,data=1;
integer passed=0,failed=0,covered=0,once=0,early_fail=0;
always #1 clk=~clk;
assert property(@(posedge clk) (req ##0 data[*254]) |-> data)passed++;else failed++;
cover property(@(posedge clk) (req ##0 data[*254]) |-> data)covered++;
assert property(@(posedge clk) (req ##0 data) |=> data)once++;
assert property(@(posedge clk) (req ##0 (!data)[*254]) |-> 0)else early_fail++;
initial begin #2;req=0;#512;
$display("TRACE antecedent-boundary %0d %0d %0d %0d %0d",passed,failed,covered,once,early_fail);
if(passed!=1||failed!=0||covered!=1||once!=1||early_fail!=0)$fatal(1,"antecedent boundary");$finish;end
endmodule
''')
(p/'parallel.sv').write_text('`timescale 1ns/1ps\nmodule lane #(parameter PERIOD=5,EDGES=20)(output integer passed=0);\nreg clk=0,a=1;integer failed=0;\ninitial repeat(EDGES) #(PERIOD)clk=~clk;\nsequence prefix;a ##2 a;endsequence\nassert property(@(posedge clk) prefix |=> a)passed++;else failed++;\nendmodule\nmodule top;\nwire [31:0] one,two;\nlane #(5,20)a(one);lane #(7,14)b(two);\nendmodule\n')
