`timescale 1ns/1ps
module top;integer q=0,r=0,t=0,k=0;
initial begin
 for(k=0;k<3;k++)begin
  fork : race
   begin #2;disable race;q=99;end
   begin fork begin #10;r=99;end begin #0;#8;t=99;end join end
  join
  q=q+1;
 end
 #20;$display("TRACE nested %0d %0d %0d %0t",q,r,t,$time);$finish;
end
endmodule
