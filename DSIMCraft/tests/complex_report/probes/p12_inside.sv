// probe: inside operator
`timescale 1ns/1ps
module tb;
    reg [3:0] v = 4'd6;
    reg hit1, hit2;
    initial begin
        hit1 = v inside {4'd2, 4'd4, 4'd6};
        hit2 = v inside {[4'd7 : 4'd9]};
        if (hit1 === 1'b1 && hit2 === 1'b0)
            $display("PROBE_INSIDE: ok");
        else
            $display("PROBE_INSIDE: BAD %b %b", hit1, hit2);
        $finish;
    end
endmodule
