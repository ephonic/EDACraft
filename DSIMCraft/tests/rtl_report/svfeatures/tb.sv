`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0, go = 0;
    reg [7:0] in_a = 0;
    wire [16:0] packed_out;
    wire [1:0] state_o;
    wire done_o;
    wire [7:0] ones_cnt;

    sv_features dut(.clk(clk), .rst_n(rst_n), .go(go), .in_a(in_a),
                    .packed_out(packed_out), .state_o(state_o), .done_o(done_o), .ones_cnt_o(ones_cnt));

    always #5 clk = ~clk;

    integer errors;
    reg [16:0] exp;
    initial begin
        errors = 0;
        @(posedge clk); #1; rst_n = 1; #1;

        // IDLE -> RUN -> DONE -> IDLE
        go = 1; in_a = 8'hA5;          // A5 ^ 5A = FF, wr = A5[0] = 1
        @(posedge clk); #1; go = 0;
        if (state_o !== 2'd1) begin errors++; $display("FAIL state after go: %0d", state_o); end
        @(posedge clk); #1;
        if (state_o !== 2'd2) begin errors++; $display("FAIL state RUN->DONE: %0d", state_o); end
        if (done_o !== 1'b1) begin errors++; $display("FAIL done not asserted"); end
        exp = {8'hA5, 8'hFF, 1'b1};
        if (packed_out !== exp) begin errors++; $display("FAIL packed struct: got=%h exp=%h", packed_out, exp); end
        @(posedge clk); #1;
        if (state_o !== 2'd0) begin errors++; $display("FAIL state DONE->IDLE: %0d", state_o); end
        if (done_o !== 1'b0) begin errors++; $display("FAIL done not deasserted"); end

        // $countones: registered, appears 1 cycle after input
        in_a = 8'h0F; @(posedge clk); #1; @(posedge clk); #1;
        if (ones_cnt !== 8'd4) begin errors++; $display("FAIL countones: %0d", ones_cnt); end

        if (errors == 0) $display("SV_TEST: ALL PASS");
        else $display("SV_TEST: %0d ERRORS", errors);
        #20 $finish;
    end
endmodule
