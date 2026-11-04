// probe: signedness-loss scope in ternary branches (>>> confirmed; others?)
`timescale 1ns/1ps
module tb;
    reg [31:0] a = 32'hFFFFFFFE;   // -2
    reg [31:0] b = 32'h00000003;
    reg        sel = 1'b1;
    reg [4:0]  sh = 5'd1;

    // direct (correct references)
    wire [31:0] d_sra   = $signed(a) >>> sh;               // -1 = FFFFFFFF
    wire [31:0] d_div   = $signed(a) / $signed(b);         // 0 (trunc -2/3 = 0)
    wire [31:0] d_mod   = $signed(a) % $signed(b);         // -2
    wire [31:0] d_cmp   = $signed(a) < $signed(b) ? 32'd1 : 32'd0;  // 1
    wire [31:0] d_mul   = $signed(b) * $signed(b);         // 9

    // ternary-wrapped (suspects)
    wire [31:0] t_sra = sel ? ($signed(a) >>> sh) : 32'd0;
    wire [31:0] t_div = sel ? ($signed(a) / $signed(b)) : 32'd0;
    wire [31:0] t_mod = sel ? ($signed(a) % $signed(b)) : 32'd0;
    wire [31:0] t_cmp = sel ? (($signed(a) < $signed(b)) ? 32'd1 : 32'd0) : 32'd0;
    wire [31:0] t_mul = sel ? ($signed(b) * $signed(b)) : 32'd0;
    wire [31:0] n     = sel ? ($signed(a) >>> sh) : ($signed(a) >>> sh);

    initial begin
        #1;
        if (t_sra === d_sra) $display("sra  in ternary: ok");
        else                 $display("sra  in ternary: BUG got=%h want=%h", t_sra, d_sra);
        if (t_div === d_div) $display("div  in ternary: ok");
        else                 $display("div  in ternary: BUG got=%h want=%h", t_div, d_div);
        if (t_mod === d_mod) $display("mod  in ternary: ok");
        else                 $display("mod  in ternary: BUG got=%h want=%h", t_mod, d_mod);
        if (t_cmp === d_cmp) $display("cmp  in ternary: ok");
        else                 $display("cmp  in ternary: BUG got=%h want=%h", t_cmp, d_cmp);
        if (t_mul === d_mul) $display("mul  in ternary: ok");
        else                 $display("mul  in ternary: BUG got=%h want=%h", t_mul, d_mul);
        if (n === 32'hFFFFFFFF) $display("sra both-branch ternary: ok");
        else                    $display("sra both-branch ternary: BUG %h", n);
        $finish;
    end
endmodule
