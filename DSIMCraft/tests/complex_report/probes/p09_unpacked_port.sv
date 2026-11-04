// probe: unpacked array as module port
`timescale 1ns/1ps
module sub (input wire [7:0] bytes_in [0:3], output wire [7:0] sum);
    assign sum = bytes_in[0] + bytes_in[1] + bytes_in[2] + bytes_in[3];
endmodule

module tb;
    reg [7:0] arr [0:3];
    wire [7:0] s;
    sub u (arr, s);
    initial begin
        arr[0] = 1; arr[1] = 2; arr[2] = 3; arr[3] = 4;
        #1;
        if (s == 8'd10) $display("PROBE_UNPACKED_PORT: ok");
        else            $display("PROBE_UNPACKED_PORT: BAD %0d", s);
        $finish;
    end
endmodule
