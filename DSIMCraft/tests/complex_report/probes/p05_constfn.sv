// probe: localparam initialized with function call (elaboration-time evaluation)
`timescale 1ns/1ps
module tb;
    function automatic integer dbl(input integer x);
        dbl = 2 * x;
    endfunction
    localparam integer D8 = dbl(8);
    initial begin
        if (D8 == 16) $display("PROBE_CONSTFN: ok 16");
        else          $display("PROBE_CONSTFN: BAD %0d", D8);
        $finish;
    end
endmodule
