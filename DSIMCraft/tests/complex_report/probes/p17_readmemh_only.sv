// probe: $readmemh only
`timescale 1ns/1ps
module tb;
    reg [7:0] mem [0:3];
    initial begin
        mem[0] = 0; mem[1] = 0; mem[2] = 0; mem[3] = 0;
        $readmemh("mem.hex", mem);
        if (mem[0] == 8'hDE && mem[1] == 8'hAD && mem[2] == 8'hBE && mem[3] == 8'hEF)
            $display("PROBE_READMEMH2: ok");
        else
            $display("PROBE_READMEMH2: BAD %h %h %h %h", mem[0], mem[1], mem[2], mem[3]);
        $finish;
    end
endmodule
