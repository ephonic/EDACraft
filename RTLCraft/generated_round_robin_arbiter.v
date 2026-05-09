module RoundRobinArbiter (
    input clk,
    input rst,
    input [7:0] reqs,
    output reg [7:0] grants
);

    logic [15:0] double_reqs;
    logic [15:0] shifted;
    logic [7:0] masked;
    logic [7:0] grant_vec;
    logic [2:0] grant_idx;
    logic [2:0] pe_masked;
    logic [2:0] pe_unmasked;
    logic pe_masked_valid;
    reg [2:0] pointer;

    always @(*) begin
        double_reqs = {reqs, reqs};
        shifted = (double_reqs >> pointer);
        masked = shifted[7:0];
        pe_masked = 0;
        if ((masked[7] == 1)) begin
            pe_masked = 7;
        end else begin
        end
        if ((masked[6] == 1)) begin
            pe_masked = 6;
        end else begin
        end
        if ((masked[5] == 1)) begin
            pe_masked = 5;
        end else begin
        end
        if ((masked[4] == 1)) begin
            pe_masked = 4;
        end else begin
        end
        if ((masked[3] == 1)) begin
            pe_masked = 3;
        end else begin
        end
        if ((masked[2] == 1)) begin
            pe_masked = 2;
        end else begin
        end
        if ((masked[1] == 1)) begin
            pe_masked = 1;
        end else begin
        end
        if ((masked[0] == 1)) begin
            pe_masked = 0;
        end else begin
        end
        pe_masked_valid = (masked != 0);
        pe_unmasked = 0;
        if ((reqs[7] == 1)) begin
            pe_unmasked = 7;
        end else begin
        end
        if ((reqs[6] == 1)) begin
            pe_unmasked = 6;
        end else begin
        end
        if ((reqs[5] == 1)) begin
            pe_unmasked = 5;
        end else begin
        end
        if ((reqs[4] == 1)) begin
            pe_unmasked = 4;
        end else begin
        end
        if ((reqs[3] == 1)) begin
            pe_unmasked = 3;
        end else begin
        end
        if ((reqs[2] == 1)) begin
            pe_unmasked = 2;
        end else begin
        end
        if ((reqs[1] == 1)) begin
            pe_unmasked = 1;
        end else begin
        end
        if ((reqs[0] == 1)) begin
            pe_unmasked = 0;
        end else begin
        end
        if ((pe_masked_valid == 1)) begin
            grant_idx = ((pe_masked + pointer) & 7);
        end else begin
            grant_idx = pe_unmasked;
        end
        grant_vec = 0;
        if ((grant_idx == 0)) begin
            grant_vec = 1;
        end else begin
        end
        if ((grant_idx == 1)) begin
            grant_vec = 2;
        end else begin
        end
        if ((grant_idx == 2)) begin
            grant_vec = 4;
        end else begin
        end
        if ((grant_idx == 3)) begin
            grant_vec = 8;
        end else begin
        end
        if ((grant_idx == 4)) begin
            grant_vec = 16;
        end else begin
        end
        if ((grant_idx == 5)) begin
            grant_vec = 32;
        end else begin
        end
        if ((grant_idx == 6)) begin
            grant_vec = 64;
        end else begin
        end
        if ((grant_idx == 7)) begin
            grant_vec = 128;
        end else begin
        end
        if ((reqs == 0)) begin
            grant_vec = 0;
        end else begin
        end
        grants = grant_vec;
    end

    always @(posedge clk) begin
        if ((rst == 1)) begin
            pointer <= 0;
        end else begin
            if ((reqs != 0)) begin
                pointer <= ((grant_idx + 1) & 7);
            end
        end
    end

endmodule