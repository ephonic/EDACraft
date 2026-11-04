// probe: mutable package variable
`timescale 1ns/1ps
package counter_pkg;
    int count = 0;
    function void tick();
        count = count + 1;
    endfunction
endpackage

module tb;
    import counter_pkg::*;
    initial begin
        tick(); tick(); tick();
        if (count == 3) $display("PROBE_PKGVAR: ok 3");
        else            $display("PROBE_PKGVAR: BAD %0d", count);
        $finish;
    end
endmodule
