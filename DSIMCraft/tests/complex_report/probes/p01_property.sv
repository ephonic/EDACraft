// probe: concurrent assertions (property/assert property)
`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0;
    reg [3:0] cnt = 0;
    always #5 clk = ~clk;
    always_ff @(posedge clk or negedge rst_n)
        if (!rst_n) cnt <= 0; else cnt <= cnt + 1;

    property p_no_overflow;
        @(posedge clk) disable iff (!rst_n) (cnt < 15);
    endproperty
    assert property (p_no_overflow) else $display("ASSERT-FIRED cnt=%0d", cnt);

    initial begin
        @(posedge clk); #1; rst_n = 1;
        repeat (20) @(posedge clk);
        $display("PROBE_PROPERTY: completed");
        $finish;
    end
endmodule
