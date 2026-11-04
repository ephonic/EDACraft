// Independent literal expectations: unsigned and signed conditional branches.
`timescale 1ns/1ps
module tb;
    reg [31:0] a=32'hfffffffe,b=32'd3;
    reg sel=1;
    reg [4:0] sh=1;
    wire [31:0] unsigned_sra=sel ? ($signed(a) >>> sh) : 32'd0;
    wire [31:0] unsigned_div=sel ? ($signed(a) / $signed(b)) : 32'd0;
    wire [31:0] unsigned_mod=sel ? ($signed(a) % $signed(b)) : 32'd0;
    wire [31:0] signed_sra=sel ? ($signed(a) >>> sh) : 32'sd0;
    wire [31:0] signed_div=sel ? ($signed(a) / $signed(b)) : 32'sd0;
    wire [31:0] signed_mod=sel ? ($signed(a) % $signed(b)) : 32'sd0;
    initial begin
        #1;
        if(unsigned_sra!==32'h7fffffff || unsigned_div!==32'h55555554 || unsigned_mod!==32'h00000002)
            $fatal(1,"unsigned conditional context differs");
        if(signed_sra!==32'hffffffff || signed_div!==32'h00000000 || signed_mod!==32'hfffffffe)
            $fatal(1,"signed conditional context differs");
        $display("PROBE_CONTEXT: unsigned=%h,%h,%h signed=%h,%h,%h",unsigned_sra,unsigned_div,unsigned_mod,signed_sra,signed_div,signed_mod);
        sel=0;
        #1;
        if(unsigned_sra!==0 || unsigned_div!==0 || unsigned_mod!==0 || signed_sra!==0 || signed_div!==0 || signed_mod!==0)
            $fatal(1,"unselected branch differs");
        $display("PROBE_CONTEXT: PASS");
        $finish;
    end
endmodule
