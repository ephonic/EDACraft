`timescale 1ns/1ps
module t04;
    reg clk = 0; reg x = 1; reg conc_fail = 0;
    always #5 clk = ~clk;
    property p_x; @(posedge clk) x |=> x; endproperty
    a_x: assert property (p_x) else conc_fail = 1;
    initial begin #40;
        if (!conc_fail) $display("T04_CONC_ASSERT PASS"); else $display("T04_CONC_ASSERT FAIL");
        $finish;
    end
endmodule
