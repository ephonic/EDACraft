module tb;
    reg clk = 0; always #5 clk = ~clk;
    logic [3:0] v;
    covergroup cg @(posedge clk);
        cp: coverpoint v { bins lo = {[0:7]}; bins hi = {[8:15]}; }
    endgroup
    cg c;
    integer i;
    initial begin
        c = new(); v = 0;
        for (i = 0; i < 16; i = i + 1) begin
            @(negedge clk); v = i[3:0];
        end
        repeat (3) @(posedge clk);
        $display("PROBE_COVER: coverage=%0f", c.get_coverage());
        $finish;
    end
endmodule
