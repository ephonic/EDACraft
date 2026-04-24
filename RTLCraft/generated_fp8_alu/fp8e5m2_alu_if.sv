interface fp8e5m2_alu_if (input logic clk);

    logic rst_n;
    logic i_valid;
    logic [7:0] a;
    logic [7:0] b;
    logic [2:0] op;
    logic o_ready;
    logic i_ready;
    logic o_valid;
    logic [7:0] result;
    logic [3:0] flags;

    clocking cb @(posedge clk);
        output i_valid;
        output [7:0] a;
        output [7:0] b;
        output [2:0] op;
        output o_ready;
        input  i_ready;
        input  o_valid;
        input  [7:0] result;
        input  [3:0] flags;
    endclocking

    modport MP (clocking cb);
endinterface : fp8e5m2_alu_if
