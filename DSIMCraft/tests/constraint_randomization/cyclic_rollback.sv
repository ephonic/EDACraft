`timescale 1ps/1ps
module top;
 class C;
  randc logic [1:0] a;
  rand bit [3:0] b;
  bit impossible=0;
  int pre_calls=0,post_calls=0;
  constraint cb {b==a+1;}
  constraint cf {if(impossible){0;}}
  function void pre_randomize();pre_calls++;endfunction
  function void post_randomize();post_calls++;endfunction
 endclass
 C c;
 bit [3:0] seen;
 bit [1:0] saved;
 int observed;
 initial begin
  c=new;if(!c.randomize())$fatal(1,"first");seen[c.a]=1;saved=c.a;
  c.a.rand_mode(0);
  if(!c.randomize()||c.a!==saved)$fatal(1,"disabled cyclic property");
  c.a.rand_mode(1);
  #2;if(!c.randomize()||seen[c.a])$fatal(1,"resumed cyclic property");seen[c.a]=1;observed=3;
  #1;saved=c.a;c.impossible=1;
  if(c.randomize()||c.a!==saved||c.pre_calls!=4||c.post_calls!=3)$fatal(1,"failed draw consumed state");
  c.impossible=0;seen=0;
  repeat(4)begin
   if(!c.randomize()||seen[c.a])$fatal(1,"failed call did not restart cycle");seen[c.a]=1;
  end
  if(seen!=15)$fatal(1,"history incomplete");observed=9;
  #2;$display("TRACE constraints cyclic checkpoint failure disable resume pass");$finish;
 end
endmodule
