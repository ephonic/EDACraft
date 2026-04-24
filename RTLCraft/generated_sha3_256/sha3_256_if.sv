interface sha3_256_if (input logic clk);

    logic rst_n;
    logic i_valid;
    logic [1087:0] block;
    logic [7:0] block_len;
    logic last_block;
    logic o_ready;
    logic i_ready;
    logic o_valid;
    logic [255:0] hash;

    clocking cb @(posedge clk);
        output i_valid;
        output [1087:0] block;
        output [7:0] block_len;
        output last_block;
        output o_ready;
        input  i_ready;
        input  o_valid;
        input  [255:0] hash;
    endclocking

    modport MP (clocking cb);
endinterface : sha3_256_if
