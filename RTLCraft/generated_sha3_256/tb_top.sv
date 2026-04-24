`timescale 1ns/1ps

module tb_top;

    logic clk;
    logic rst_n;
    sha3_256_if vif (.clk(clk));

    sha3_256 dut (
        .clk(vif.clk),
        .rst_n(rst_n),
        .i_valid(vif.i_valid),
        .block(vif.block),
        .block_len(vif.block_len),
        .last_block(vif.last_block),
        .o_ready(vif.o_ready),
        .i_ready(vif.i_ready),
        .o_valid(vif.o_valid),
        .hash(vif.hash)
    );

    initial begin
        uvm_config_db # (virtual sha3_256_if)::set(null, "*", "vif", vif);
        run_test("test");
    end

{rstr}
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

endmodule
