// probe: concurrent assertion semantics detail
`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0;
    reg [4:0] cnt = 0;
    reg fired_fail = 0;
    always #5 clk = ~clk;
    always_ff @(posedge clk or negedge rst_n)
        if (!rst_n) cnt <= 0; else cnt <= cnt + 1;

    // expect hold: cnt<15 for first 15 cycles after reset, then >=15
    property p_lt15;
        @(posedge clk) disable iff (!rst_n) (cnt < 15);
    endproperty

    // antecedent=>consequent: after cnt==3, next cycle cnt==4
    property p_step;
        @(posedge clk) disable iff (!rst_n) (cnt == 3) |=> (cnt == 4);
    endproperty

    reg lt15_fail = 0, step_fail = 0;
    reg [4:0] fired_at = 0;

    a_lt15: assert property (p_lt15)
        else lt15_fail = 1;
    a_lt15_at: assert property (p_lt15)
        else fired_at = cnt;

    a_step: assert property (p_step)
        else step_fail = 1;

    initial begin
        @(posedge clk); #1; rst_n = 1;
        repeat (20) @(posedge clk);
        #1;
        if (lt15_fail === 1'b1 && fired_at >= 5'd15 && step_fail === 1'b0)
            $display("PROBE_ASSERT2: ok (per-cycle firing, |=> held)");
        else
            $display("PROBE_ASSERT2: BAD lt15=%b@%0d step=%b",
                     lt15_fail, fired_at, step_fail);
        $finish;
    end
endmodule
