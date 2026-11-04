`timescale 1ps/1ps
module top;
 class Base;
  bit [15:0] q[$:3]={16'h1234,16'h5678};
 endclass
 class C extends Base;
  int normal[$];
 endclass
 C c,alias_c,other;
 bit [15:0] copied[$];
 int total;
 initial begin
  c=new;other=new;alias_c=c;
  if(c.q.size()!=2||c.q[$]!=16'h5678)$fatal(1,"queue initializer last");
  c.q[0][7:0]=8'hab;c.q[c.q.size()]=16'h9abc;
  c.q.insert(1,16'hdead);c.q.push_back(16'hffff);
  if(c.q.size()!=4||alias_c.q[0]!=16'h12ab||c.q[$]!=16'h9abc)$fatal(1,"bounded queue and alias");
  if(c.q.pop_front()!=16'h12ab||c.q.pop_back()!=16'h9abc)$fatal(1,"queue pop");
  c.q.delete(0);c.q.push_front(16'h0bad);
  copied=c.q;other.q=copied;c.q={};
  if(copied.size()!=2||other.q.size()!=2||c.q.size()!=0)$fatal(1,"queue copy values");
  other.q[0]=16'h1111;if(copied[0]!=16'h0bad)$fatal(1,"copy must not alias");
  c.normal={2,3,5};foreach(c.normal[i])total+=c.normal[i];
  if(total!=10)$fatal(1,"procedural foreach class queue");
  c.normal.delete();if(c.normal.size()!=0)$fatal(1,"delete all");
  $display("TRACE class queues constructors copy alias bounded selects methods pass");$finish;
 end
endmodule
