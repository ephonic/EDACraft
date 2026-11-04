`timescale 1ps/1ps
module top;
 class Packet;
  rand bit [7:0] data[];
  randc bit [1:0] phase;
  int requested=2;
  constraint sizes {data.size()==requested;}
  constraint values_c {foreach(data[i])data[i] inside {[1:50]};}
 endclass
 Packet p;bit [3:0] seen;int observed,snapshot;
 initial begin
  p=new;p.srandom(21);
  if(!p.randomize())$fatal(1,"first");seen[p.phase]=1;
  #2;p.requested=3;
  if(!p.randomize()||seen[p.phase]||p.data.size()!=3)$fatal(1,"second");seen[p.phase]=1;
  foreach(p.data[i])snapshot+=p.data[i];observed=9;
  #1;p.requested=4;
  if(!p.randomize()||seen[p.phase]||p.data.size()!=4)$fatal(1,"third");seen[p.phase]=1;
  foreach(p.data[i])snapshot+=p.data[i];observed=7;
  if(!p.randomize()||seen[p.phase])$fatal(1,"cycle");seen[p.phase]=1;
  if(seen!=15)$fatal(1,"cyclic state with arrays");
  #2;$display("TRACE class dynamic size data rng cycles checkpoint pass");$finish;
 end
endmodule
