`timescale 1ns/1ps
interface bus_if (input wire clk);
    logic req, gnt;
    logic [7:0] addr;
    modport m (output req, addr, input clk, gnt);
    modport s (input clk, req, addr, output gnt);
endinterface
module master (bus_if.m b, input wire [7:0] a);
    always @(posedge b.clk) begin b.req <= 1'b1; b.addr <= a; end
endmodule
module slave (bus_if.s b);
    always @(posedge b.clk) b.gnt <= b.req;
endmodule
module deep4_if;
    reg clk = 0; reg [7:0] a = 8'h5C;
    always #5 clk = ~clk;
    bus_if bif(clk);
    master m (bif, a);
    slave s (bif);
    initial begin
        repeat (3) @(posedge clk); #1;
        if (bif.req === 1'b1 && bif.gnt === 1'b1 && bif.addr === 8'h5C)
            $display("D4 INTERFACE PASS");
        else $display("D4 INTERFACE FAIL req=%b gnt=%b addr=%h", bif.req, bif.gnt, bif.addr);
        $finish;
    end
endmodule
