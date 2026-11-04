// probe: variable-index NBA into unpacked array, index reg updated by NBA in same block
`timescale 1ns/1ps
module tb;
    reg clk = 0;
    always #5 clk = ~clk;
    reg [9:0] idx = 0;
    reg [31:0] d = 0;
    reg [31:0] mem [0:1023];
    reg go = 0;
    integer i;

    always @(posedge clk) begin
        if (go) begin
            mem[idx] <= d;
            $display("wr mem[%0d] <= %h @%0t", idx, d, $time);
            idx <= idx + 10'd7;
            d   <= d + 32'd1;
        end
    end

    initial begin
        for (i = 0; i < 32; i = i + 1) mem[i] = 32'd0;
        @(posedge clk); #1;
        go = 1; idx = 10'd3; d = 32'hAA;
        repeat (4) @(posedge clk); #1;
        go = 0;
        repeat (2) @(posedge clk); #1;
        // expect mem[3]=AA mem[10]=AB mem[17]=AC mem[24]=AD
        for (i = 0; i < 32; i = i + 1)
            if (mem[i] !== 32'd0)
                $display("mem[%0d]=%h", i, mem[i]);
        if (mem[3] === 32'hAA && mem[10] === 32'hAB && mem[17] === 32'hAC && mem[24] === 32'hAD)
            $display("PROBE_VARRD: ok");
        else
            $display("PROBE_VARRD: BAD %h %h %h %h", mem[3], mem[10], mem[17], mem[24]);
        $finish;
    end
endmodule
