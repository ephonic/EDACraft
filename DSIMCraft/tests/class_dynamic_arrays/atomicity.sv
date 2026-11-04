module top;
 class Packet;
  rand bit [7:0] data[];
  rand int tag;
  int requested=3;
  bit impossible;
  int pre_count,post_count;
  constraint size_c {data.size()==requested;}
  constraint values_c {tag==17;foreach(data[i]){data[i]==i+10;if(impossible)data[i]<0;}}
  function void pre_randomize();pre_count++;endfunction
  function void post_randomize();post_count++;endfunction
 endclass
 Packet p;int observed;
 initial begin
  p=new;if(!p.randomize())$fatal(1,"initial draw");
  p.requested=-1;
  if(p.randomize()||p.data.size()!=3||p.data[2]!=12||p.tag!=17)$fatal(1,"size failure atomicity");
  p.requested=3;p.impossible=1;
  if(p.randomize()||p.data.size()!=3||p.data[2]!=12||p.tag!=17)$fatal(1,"element failure atomicity");
  p.impossible=0;p.requested=5;
  if(!p.randomize()||p.data.size()!=5||p.data[4]!=14)$fatal(1,"successful resize after failure");
  p.data.rand_mode(0);p.requested=4;
  if(p.randomize()||p.data.size()!=5||p.data[4]!=14)$fatal(1,"inactive size constraint");
  if(p.pre_count!=5||p.post_count!=2)$fatal(1,"failed callback accounting");
  observed=p.tag;
  $display("TRACE class dynamic unsat sizes elements atomic callbacks pass");$finish;
 end
endmodule
