`timescale 1ns/1ps
module lane #(parameter PERIOD=1)(output integer q=0);
function automatic integer next_value(input integer n);
 static integer calls=0;
 calls++;
 return calls+n;
endfunction
initial begin
 q=next_value(1);
 #PERIOD;q=next_value(2);
 #PERIOD;q=next_value(3);
end
endmodule
module top;
wire signed[31:0] a,b;
lane u(a);lane #(.PERIOD(2))v(b);
endmodule
