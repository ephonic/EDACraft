`timescale 1ps/1ps
module top;
 class C;
  rand bit [7:0] a;
  int pre_calls=0,post_calls=0;
  bit impossible=0;
  constraint range_c {a inside {[1:200]};if(impossible){a==0;}}
  function void pre_randomize();pre_calls++;endfunction
  function void post_randomize();post_calls++;endfunction
 endclass
 C c;
 int observed;
 bit [7:0] draw,previous,seeded;
 initial begin
  c=new;c.srandom(123);if(!c.randomize())$fatal(1,"first draw");seeded=c.a;
  c.srandom(123);if(!c.randomize()||c.a!=seeded)$fatal(1,"object seeding");
  #2;if(!c.randomize())$fatal(1,"draw after delay");draw=c.a;observed=3;
  #1;previous=c.a;c.impossible=1;
  if(c.randomize()||c.a!=previous)$fatal(1,"unsat changed object");
  if(c.pre_calls!=4||c.post_calls!=3)$fatal(1,"failure callbacks");
  c.impossible=0;c.rand_mode(0);
  if(!c.randomize()||c.a!=previous)$fatal(1,"disabled rand_mode");
  c.rand_mode(1);if(!c.randomize())$fatal(1,"reenabled randomization");
  draw=c.a;observed=9;
  #2;$display("TRACE constraints checkpoint rng callbacks modes pass");$finish;
 end
endmodule
