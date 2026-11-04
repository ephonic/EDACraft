// CLI probe: +incdir/+define include file
`timescale 1ns/1ps
`include "cli_inc.svh"
module top;
    initial begin
        `ifdef DEF_SET
            $display("CLI_PROBE: ok W_INC=%0d", `W_INC);
        `else
            $display("CLI_PROBE: DEF_SET missing");
        `endif
        $finish;
    end
endmodule
