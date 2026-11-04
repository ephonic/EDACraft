// probe: $readmemh / $writememh
`timescale 1ns/1ps
module tb;
    reg [7:0] mem [0:3];
    integer i;
    initial begin
        mem[0] = 0; mem[1] = 0; mem[2] = 0; mem[3] = 0;
        $readmemh("mem.hex", mem);
        if (mem[0] == 8'hDE && mem[1] == 8'hAD && mem[2] == 8'hBE && mem[3] == 8'hEF)
            $display("PROBE_READMEMH: ok");
        else
            $display("PROBE_READMEMH: BAD %h %h %h %h", mem[0], mem[1], mem[2], mem[3]);
        for (i = 0; i < 4; i = i + 1) mem[i] = mem[i] ^ 8'hFF;
        $writememh("mem_out.hex", mem);
        $display("PROBE_READMEMH: writememh done");
        $finish;
    end
endmodule
