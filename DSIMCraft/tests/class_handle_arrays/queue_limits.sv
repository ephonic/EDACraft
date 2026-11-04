module top;
 class Packet;
  rand bit [7:0] q[$:2];
  int requested=3;
  int pre_count,post_count;
  constraint size_c {q.size()==requested;}
  constraint values_c {foreach(q[i])q[i]==i+5;}
  function void pre_randomize();pre_count++;endfunction
  function void post_randomize();post_count++;endfunction
 endclass
 class Retain;rand bit [7:0] q[$];endclass
 Packet p;Retain r;int observed;
 initial begin
  p=new;if(!p.randomize()||p.q.size()!=3||p.q[2]!=7)$fatal(1,"bound capacity");
  p.requested=4;
  if(p.randomize()||p.q.size()!=3||p.q[2]!=7)$fatal(1,"capacity must constrain solver");
  if(p.pre_count!=2||p.post_count!=1)$fatal(1,"capacity callbacks");
  p.requested=0;if(!p.randomize()||p.q.size()!=0)$fatal(1,"empty queue");
  r=new;if(!r.randomize()||r.q.size()!=0)$fatal(1,"unconstrained empty length");
  r.q.push_back(17);r.q.push_back(18);
  if(!r.randomize()||r.q.size()!=2)$fatal(1,"unconstrained existing length");
  observed=p.post_count;
  $display("TRACE random bounded queue unsat atomicity empty retained sizes pass");$finish;
 end
endmodule
