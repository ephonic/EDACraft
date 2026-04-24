`timescale 1ns/1ps

module tb_top;

    logic clk;
    decoder_8b10b_if vif (.clk(clk));

    decoder_8b10b dut (
        .clk_in(vif.clk_in),
        .reset_in(vif.reset_in),
        .control_in(vif.control_in),
        .decoder_in(vif.decoder_in),
        .decoder_valid_in(vif.decoder_valid_in),
        .decoder_out(vif.decoder_out),
        .decoder_valid_out(vif.decoder_valid_out),
        .control_out(vif.control_out)
    );

    initial begin
        uvm_config_db # (virtual decoder_8b10b_if)::set(null, "*", "vif", vif);
        run_test("decoder_test");
    end


    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

endmodule
