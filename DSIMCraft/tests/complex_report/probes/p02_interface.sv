// probe: interface + modport
`timescale 1ns/1ps
interface bus_if (input wire clk);
    logic        req, gnt;
    logic [7:0]  addr;
    modport m (output req, addr, input gnt, input clk);
    modport s (input  req, addr, output gnt, input clk);
endinterface

module slave (bus_if.s s_if);
    always_ff @(posedge s_if.clk) s_if.gnt <= s_if.req;
endmodule

module tb;
    reg clk = 0;
    always #5 clk = ~clk;
    bus_if bif (clk);
    slave u_s (bif);
    initial begin
        bif.req = 0; bif.addr = 0;
        @(posedge clk); #1; bif.req = 1; bif.addr = 8'h42;
        @(posedge clk); #1;
        if (bif.gnt === 1'b1) $display("PROBE_INTERFACE: gnt ok");
        else                  $display("PROBE_INTERFACE: gnt BAD");
        $finish;
    end
endmodule
