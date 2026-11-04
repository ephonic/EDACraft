`timescale 1ns/1ps
module dutd #(parameter W=8, D=8)(input wire clk, input wire rst_n, input wire wen, input wire [W-1:0] wdata, output reg [$clog2(D)-1:0] cnt);
    reg [W-1:0] mem [0:D-1];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) cnt <= 0;
        else if (wen) begin mem[cnt] <= wdata; cnt <= cnt + 1; end
    end
endmodule
module top;
    reg clk=0, rst_n=0, wen=0; reg [7:0] wd=0; wire [2:0] cnt;
    dutd u(.clk(clk),.rst_n(rst_n),.wen(wen),.wdata(wd),.cnt(cnt));
    always #5 clk = ~clk;
    integer errors;
    initial begin
        errors = 0;
        @(posedge clk); #1 rst_n = 1;
        wen=1; wd=8'h42; @(posedge clk); #1; wd=8'h99; @(posedge clk); #1; wen=0;
        // hierarchical: internal array element, internal cnt via name clash with tb 'cnt'? use u.cnt & u.mem
        if (u.mem[0] !== 8'h42) begin errors++; $display("FAIL u.mem[0]=%h", u.mem[0]); end
        if (u.mem[1] !== 8'h99) begin errors++; $display("FAIL u.mem[1]=%h", u.mem[1]); end
        if (u.cnt !== 3'd2)     begin errors++; $display("FAIL u.cnt=%0d", u.cnt); end
        // hierarchical reference INTO generate/params
        if (u.W !== 8)          begin errors++; $display("FAIL u.W=%0d", u.W); end
        if (errors==0) $display("H_DEEP PASS (array+param hier access)");
        $finish;
    end
endmodule
