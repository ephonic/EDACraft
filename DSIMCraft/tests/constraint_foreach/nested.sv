`timescale 1ps/1ps
module top;
 class Limits #(int N=3);
  rand bit [95:0] x;
  int lower[int unsigned];
  int upper[string];
  constraint c {
   x inside {[96'h100000000000000000000000:96'h10000000000000000000000f]};
   foreach(lower[i]) {
    foreach(upper[i]) if(i=="max") {x<96'h100000000000000000000000+upper[i];}
    x>96'h100000000000000000000000+lower[i];
   }
  }
 endclass
 Limits #(3) a;Limits #(5) b;
 int observed;
 initial begin
  a=new;b=new;a.lower[-1]=6;a.upper["max"]=8;b.lower[-1]=9;b.upper["max"]=11;
  if(!a.randomize()||a.x!=96'h100000000000000000000007)$fatal(1,"nested key shadow and wide");
  if(!b.randomize()||b.x!=96'h10000000000000000000000a)$fatal(1,"specialization clone");
  observed=int'(a.x)+int'(b.x);
  $display("TRACE constraint foreach nested keys specialization wide values pass");$finish;
 end
endmodule
