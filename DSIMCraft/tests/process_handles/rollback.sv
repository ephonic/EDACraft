`timescale 1ps/1ps
module top;
 process parent,child,prior;string saved;int unsigned value;int observed;
 initial begin
  parent=process::self();parent.srandom(77);saved=parent.get_randstate();
  for(int i=0;i<3;i++)begin
   fork begin
    child=process::self();if(child==prior)$fatal(1,"rollback identity");
    child.srandom(12);#1;value=$urandom();
   end join
   prior=child;
  end
  parent.set_randstate(saved);if(parent.get_randstate()!=saved)$fatal(1,"rollback RNG");
  $display("TRACE rollback %0d",observed);$finish;
 end
 initial begin #2;observed=9;#1;observed=7;end
endmodule
