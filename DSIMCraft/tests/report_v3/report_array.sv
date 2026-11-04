`timescale 1ns/1ps
module suba(input wire clk, input wire [7:0] v);
    reg [7:0] mem [0:3];
    always @(posedge clk) begin mem[0] <= v; mem[1] <= v+1; end
endmodule
module top;
    reg clk=0; reg [7:0] v=0;
    suba u(.clk(clk),.v(v));
    always #5 clk=~clk;
    initial begin
        v=8'h42; @(posedge clk); #1;
        $display("H_ARR mem[0]=%h mem[1]=%h", u.mem[0], u.mem[1]);
        $finish;
    end
endmodule
