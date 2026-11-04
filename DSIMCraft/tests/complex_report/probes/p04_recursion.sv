// probe: function recursion at runtime
`timescale 1ns/1ps
module tb;
    function automatic integer fact(input integer n);
        if (n <= 1) fact = 1;
        else        fact = n * fact(n - 1);
    endfunction
    integer r;
    initial begin
        r = fact(6);   // 720
        if (r == 720) $display("PROBE_RECURSION: ok 720");
        else          $display("PROBE_RECURSION: BAD %0d", r);
        $finish;
    end
endmodule
