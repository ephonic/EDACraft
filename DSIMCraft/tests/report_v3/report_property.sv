`timescale 1ns/1ps
module top;
    reg clk = 0; reg req = 0; reg gnt = 0;
    reg conc_fail = 0; reg conc_fire = 0;
    always #5 clk = ~clk;
    // concurrent assertion: req must be granted next cycle
    property p_req_gnt; @(posedge clk) req |=> gnt; endproperty
    a1: assert property (p_req_gnt) else conc_fail = 1;
    // expect-style/sequence probe via simple assert with implication |->
    property p_gnt_drop; @(posedge clk) gnt |-> !req; endproperty
    a2: assert property (p_gnt_drop) else conc_fail = 1;
    initial begin
        @(posedge clk); #1 req = 1; gnt = 0;
        @(posedge clk); #1 gnt = 1; req = 0;
        @(posedge clk); #1 gnt = 0;
        @(posedge clk); #1;
        if (!conc_fail) $display("D3 CONC_ASSERT PASS"); else $display("D3 CONC_ASSERT FAIL");
        $finish;
    end
endmodule
