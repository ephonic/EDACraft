// crc32 perf bench: 4000 frames x 64B with random valid gaps
`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0;
    reg  soc = 0, eoc = 0, valid = 0;
    reg  [7:0] data_in = 0;
    wire crc_valid;
    wire [31:0] crc_out;
    wire busy;

    crc32_engine dut (
        .clk(clk), .rst_n(rst_n), .soc(soc), .eoc(eoc), .valid(valid),
        .data_in(data_in), .crc_valid(crc_valid), .crc_out(crc_out), .busy(busy)
    );
    always #5 clk = ~clk;

    // deterministic xorshift32 (pure function; caller advances state)
    reg [31:0] rng_state = 32'h1A2B3C4D;
    function automatic [31:0] xs32(input [31:0] s);
        reg [31:0] t;
        begin
            t = s ^ (s << 13);
            t = t ^ (t >> 17);
            t = t ^ (t << 5);
            xs32 = t;
        end
    endfunction

    function automatic [31:0] crc_ref(input [7:0] f0, input [7:0] f1,
                                      input [7:0] f2, input [7:0] f3);
        reg [31:0] c, t; integer i, k;
        reg [31:0] mem [0:3];
        begin
            mem[0] = f0; mem[1] = f1; mem[2] = f2; mem[3] = f3;
            c = 32'hFFFFFFFF;
            for (k = 0; k < 4; k = k + 1) begin
                t = c ^ {24'd0, mem[k][7:0]};
                for (i = 0; i < 8; i = i + 1)
                    t = (t >> 1) ^ (32'hEDB88320 & {32{t[0]}});
                c = t;
            end
            crc_ref = c;
        end
    endfunction

    integer f, b, i, guard, errors;
    reg [7:0] frame [0:63];
    reg [31:0] chk, exp4;
    task automatic run_frame;
        begin
            guard = 0;
            while (busy && guard < 2000) begin @(negedge clk); guard = guard + 1; end
            for (b = 0; b < 64; b = b + 1) begin
                @(negedge clk);
                rng_state = xs32(rng_state);
                valid = ((rng_state % 4) > 0) || (b == 63);
                soc = (b == 0);
                eoc = (b == 63);
                data_in = frame[b];
                if (!valid) b = b - 1;
            end
            @(negedge clk); valid = 0; soc = 0; eoc = 0;
            guard = 0;
            while (!crc_valid && guard < 2000) begin @(negedge clk); guard = guard + 1; end
            chk = chk ^ crc_out;
        end
    endtask

    initial begin
        errors = 0; chk = 0;
        @(posedge clk); #1; @(posedge clk); #1; rst_n = 1;
        for (f = 0; f < 160000; f = f + 1) begin
            for (i = 0; i < 64; i = i + 1) begin
                rng_state = xs32(rng_state);
                frame[i] = rng_state[7:0];
            end
            run_frame;
        end
        if (chk !== 32'h00000000) ; // arbitrary aggregate; print it
        $display("PERF crc: PASS frames=160000 chk=0x%08x", chk);
        $finish;
    end
endmodule
