`timescale 1ps/1ps
module top;
 typedef enum bit [3:0] {A=2,B=7,C=13} code_t;
 class Cycler;
  randc code_t code;
 endclass
 Cycler c;bit [15:0] seen;int observed;
 initial begin
  c=new;c.srandom(92);
  if(!c.randomize())$fatal(1,"initial draw");seen[c.code]=1;
  c.code.rand_mode(0);
  if(!c.randomize()||!seen[c.code])$fatal(1,"inactive cycle");
  c.code.rand_mode(1);
  #2;if(!c.randomize()||seen[c.code])$fatal(1,"cycle second");seen[c.code]=1;observed=3;
  #1;if(!c.randomize()||seen[c.code])$fatal(1,"cycle third");seen[c.code]=1;
  if(seen!=16'h2084)$fatal(1,"sparse cycle domain");
  seen=0;
  repeat(3)begin
   if(!c.randomize()||seen[c.code])$fatal(1,"cycle restart");seen[c.code]=1;
  end
  if(seen!=16'h2084)$fatal(1,"restarted cycle domain");observed=9;
  #2;$display("TRACE constraints enum cyclic checkpoint sparse domain pass");$finish;
 end
endmodule
