// VCS-aligned oracle: unsigned alternate branch changes expression context.
`timescale 1ns/1ps
module tb;
    reg [31:0] a = 32'hFFFFFFFE;
    reg        sel = 1'b1;
    reg [4:0]  sh = 5'd10;
    // direct
    wire [31:0] r_direct = $signed(a) >>> sh;
    // via conditional expression (like pipeline forwarding mux)
    wire [31:0] fwd = sel ? a : 32'd0;
    wire [31:0] r_cond = $signed(fwd) >>> sh;
    // ternary inside expression itself
    wire [31:0] r_tern = sel ? ($signed(a) >>> sh) : (a >> sh);
    // via function
    function automatic [31:0] do_sra(input [31:0] v, input [4:0] s);
        do_sra = $signed(v) >>> s;
    endfunction
    wire [31:0] r_func = do_sra(a, sh);
    // via if/else statements (workaround candidate)
    reg [31:0] r_ifelse;
    always_comb begin
        if (sel) r_ifelse = $signed(a) >>> sh;
        else     r_ifelse = a >> sh;
    end
    initial begin
        #1;
        $display("direct=%h cond=%h tern=%h func=%h ifelse=%h (tern unsigned=003fffff)",
                 r_direct, r_cond, r_tern, r_func, r_ifelse);
        if (r_direct === 32'hFFFFFFFF && r_cond === 32'hFFFFFFFF &&
            r_func === 32'hFFFFFFFF && r_ifelse === 32'hFFFFFFFF && r_tern === 32'h003fffff)
            $display("PROBE_SRA: PASS (unsigned ternary context: tern=%h)", r_tern);
        else
            $fatal(1,"PROBE_SRA: MISMATCH");
        $finish;
    end
endmodule
