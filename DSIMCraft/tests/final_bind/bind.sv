`timescale 1ns/1ps
bind lane observer #(.WIDTH(W)) watch(.value(local_value),.selected(bits[W-1:0]));
module observer #(parameter WIDTH=1)(input wire [WIDTH-1:0] value,selected);
 final $display("WATCH %m %0d %0d",value,selected);
endmodule
module lane #(parameter W=8)(output wire[W-1:0] result);
 logic[W-1:0] local_value;logic[W+1:0] bits;
 assign result=local_value;
 initial begin local_value=0;bits=0;#1;local_value=W+1;bits=W+2;end
endmodule
module top;
 wire[3:0]a;wire[7:0]b;
 lane #(4) u(a);lane #(8) v(b);
endmodule
