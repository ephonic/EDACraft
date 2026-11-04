`timescale 1ns/1ps
module top;
  logic [31:0] a=32'hfffffffe, b=3;
  logic [5:0] sh=1;
  logic sel=1;
  int step=0;
  wire [31:0] direct_sra=$signed(a) >>> sh;
  wire [31:0] direct_div=$signed(a) / $signed(b);
  wire [31:0] direct_mod=$signed(a) % $signed(b);
  wire [31:0] unsigned_sra=sel ? ($signed(a) >>> sh) : 32'd0;
  wire [31:0] unsigned_div=sel ? ($signed(a) / $signed(b)) : 32'd0;
  wire [31:0] unsigned_mod=sel ? ($signed(a) % $signed(b)) : 32'd0;
  wire [31:0] signed_sra=sel ? ($signed(a) >>> sh) : 32'sd0;
  wire [31:0] signed_div=sel ? ($signed(a) / $signed(b)) : 32'sd0;
  wire [31:0] signed_mod=sel ? ($signed(a) % $signed(b)) : 32'sd0;
  // A cast or a function call bounds the outer unsigned type context.
  wire [31:0] cast_sra=sel ? $signed($signed(a) >>> sh) : 32'd0;
  wire [31:0] cast_div=sel ? $signed($signed(a) / $signed(b)) : 32'd0;
  wire [31:0] cast_mod=sel ? $signed($signed(a) % $signed(b)) : 32'd0;
  function automatic logic signed [31:0] shift(input logic [31:0] x,input int amount);
    return $signed(x) >>> amount;
  endfunction
  wire [31:0] function_sra=sel ? shift(a,sh) : 32'd0;
  // Width is determined before the operation. Sign and width are independent.
  wire [63:0] wide_unsigned=sel ? ($signed(a) >>> sh) : 64'd0;
  wire [63:0] wide_signed=sel ? ($signed(a) >>> sh) : 64'sd0;
  task show();
    $display("TRACE signed %0d %b %h %h %0d %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h",
      step,sel,a,b,sh,direct_sra,direct_div,direct_mod,
      unsigned_sra,unsigned_div,unsigned_mod,signed_sra,signed_div,signed_mod,
      cast_sra,cast_div,cast_mod,function_sra,wide_unsigned,wide_signed);
  endtask
  initial begin
    #1;
    if(unsigned_sra!==32'h7fffffff || unsigned_div!==32'h55555554 || unsigned_mod!==2)
      $fatal(1,"unsigned branch must propagate its type context");
    if(signed_sra!==32'hffffffff || signed_div!==0 || signed_mod!==32'hfffffffe)
      $fatal(1,"signed branches must preserve signed arithmetic");
    if(cast_sra!==direct_sra || cast_div!==direct_div || cast_mod!==direct_mod || function_sra!==direct_sra)
      $fatal(1,"cast/function boundary");
    if(wide_unsigned!==64'h000000007fffffff || wide_signed!==64'hffffffffffffffff)
      $fatal(1,"sign extension before wide arithmetic shift");
    show();
    a=32'hfffffff9;b=3;sh=2;step=1;#1;show();
    a=32'h80000000;b=32'hfffffffd;sh=31;step=2;#1;show();
    sh=32;step=3;#1;show();
    sel=0;step=4;#1;show();
    sel=1'bx;a=32'hfffffffe;b=3;sh=1;step=5;#1;show();
    sel=1'bz;step=6;#1;show();
    sel=1;a=32'h7fffffff;b=32'hfffffffd;sh=1;step=7;#1;show();
    b=0;step=8;#1;show();
    a=32'hxxxxxxfe;b=3;step=9;#1;show();
    $finish;
  end
endmodule
