`timescale 1ns/1ps

module tb_top;

    logic clk;
    logic rst_n;
    fp8e5m2_alu_if vif (.clk(clk));

    fp8e5m2_alu dut (
        .clk(vif.clk),
        .rst_n(rst_n),
        .i_valid(vif.i_valid),
        .a(vif.a),
        .b(vif.b),
        .op(vif.op),
        .o_ready(vif.o_ready),
        .i_ready(vif.i_ready),
        .o_valid(vif.o_valid),
        .result(vif.result),
        .flags(vif.flags)
    );

    initial begin
        uvm_config_db # (virtual fp8e5m2_alu_if)::set(null, "*", "vif", vif);
        run_test("test");
    end

{rstr}
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

endmodule
