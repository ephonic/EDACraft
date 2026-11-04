`timescale 1ns/1ps
module lane #(parameter PERIOD=1)(output integer total=0);
integer stamp=0,k=0;
initial begin
 for(k=0;k<3;k++)begin
  fork
   begin #PERIOD;total=total+1;end
   begin #(2*PERIOD);stamp=stamp+1;end
  join
 end
end
endmodule
module top;wire[31:0]a,b;lane #(.PERIOD(1))u(a);lane #(.PERIOD(2))v(b);endmodule
