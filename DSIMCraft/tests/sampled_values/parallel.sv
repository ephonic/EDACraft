`timescale 1ns/1ps
module lane #(parameter ID=0)(output logic done=0);
reg clk=0;integer q=ID+3,p=ID+3,checks=0,errors=0;
check: assert property(@(posedge clk) ($past(q)===p)&&($sampled(q)==q)) checks=checks+1;else errors=errors+1;
always @(posedge clk) p<=q;
initial begin
 #1;q=q+5;
 repeat(5)begin #(ID+2);clk=1;#1;clk=0;q=q+1;end
 #1;done=(checks==5&&errors==0);
end
endmodule
module top;
wire one,two;lane #(0) a(one);lane #(1) b(two);
endmodule
