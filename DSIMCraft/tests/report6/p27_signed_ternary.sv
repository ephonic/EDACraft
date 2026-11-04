// VCS-aligned oracle: test literal expectations instead of assuming identical contexts.
`timescale 1ns/1ps
module tb;
    reg [31:0] a = 32'hFFFFFFFE;   // -2
    reg [31:0] b = 32'h00000003;
    reg        sel = 1'b1;
    reg [4:0]  sh = 5'd1;

    // Standalone signed context (not an oracle for unsigned ternary branches).
    wire [31:0] d_sra   = $signed(a) >>> sh;               // -1 = FFFFFFFF
    wire [31:0] d_div   = $signed(a) / $signed(b);         // 0 (trunc -2/3 = 0)
    wire [31:0] d_mod   = $signed(a) % $signed(b);         // -2
    wire [31:0] d_cmp   = $signed(a) < $signed(b) ? 32'd1 : 32'd0;  // 1
    wire [31:0] d_mul   = $signed(b) * $signed(b);         // 9

    // The unsigned alternate branch propagates an unsigned arithmetic context.
    wire [31:0] t_sra = sel ? ($signed(a) >>> sh) : 32'd0;
    wire [31:0] t_div = sel ? ($signed(a) / $signed(b)) : 32'd0;
    wire [31:0] t_mod = sel ? ($signed(a) % $signed(b)) : 32'd0;
    wire [31:0] t_cmp = sel ? (($signed(a) < $signed(b)) ? 32'd1 : 32'd0) : 32'd0;
    wire [31:0] t_mul = sel ? ($signed(b) * $signed(b)) : 32'd0;
    wire [31:0] n     = sel ? ($signed(a) >>> sh) : ($signed(a) >>> sh);

    initial begin
        #1;
        if(d_sra!==32'hffffffff || d_div!==32'h00000000 || d_mod!==32'hfffffffe || d_cmp!==1 || d_mul!==9)
            $fatal(1,"standalone signed operations differ");
        if(t_sra!==32'h7fffffff || t_div!==32'h55555554 || t_mod!==32'h00000002)
            $fatal(1,"unsigned alternate-branch context differs");
        if(t_cmp!==1 || t_mul!==9 || n!==32'hffffffff)
            $fatal(1,"comparison, multiplication or signed branches differ");
        $display("PROBE_CONTEXT: PASS standalone=%h,%h,%h unsigned_ternary=%h,%h,%h",d_sra,d_div,d_mod,t_sra,t_div,t_mod);
        $finish;
    end
endmodule
