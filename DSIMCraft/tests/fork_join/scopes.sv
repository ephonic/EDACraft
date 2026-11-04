`timescale 1ns/1ps
module top;
integer a=0,b=0,k=0;
task automatic work(input integer n,output integer value);
 integer base=n*10;
 fork : workers
  integer local_base;
  begin local_base=base;#2;value=local_base+1;end
  begin #3;if(base!==n*10)$fatal(1,"automatic frame corrupted");end
 join
endtask
initial begin
 fork join
 for(k=0;k<3;k++)begin
  fork
   work(k,a);
   work(k+3,b);
  join
 end
 fork #0;join
 $display("TRACE scopes %0d %0d %0d %0t",a,b,k,$time);
 if(a!==21||b!==51||k!==3)$fatal(1,"scope/reuse mismatch");
 $finish;
end
endmodule
