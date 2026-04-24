interface decoder_8b10b_if (input logic clk);

    logic clk_in;
    logic reset_in;
    logic control_in;
    logic [9:0] decoder_in;
    logic decoder_valid_in;
    logic [7:0] decoder_out;
    logic decoder_valid_out;
    logic control_out;

    clocking cb @(posedge clk);
        output clk_in;
        output reset_in;
        output control_in;
        output [9:0] decoder_in;
        output decoder_valid_in;
        input  [7:0] decoder_out;
        input  decoder_valid_out;
        input  control_out;
    endclocking

    modport MP (clocking cb);
endinterface : decoder_8b10b_if
