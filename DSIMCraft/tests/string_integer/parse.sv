`timescale 1ns/1ps
module top;int count=0;integer signed_result;string source;
task check(input string text,input logic[31:0] dec,hexv,oct,bin);begin
if(text.atoi()!==dec||text.atohex()!==hexv||text.atooct()!==oct||text.atobin()!==bin)$fatal(1,"integer parsing");
count++;$display("TRACE parse %0d %h %h %h %h",count,text.atoi(),text.atohex(),text.atooct(),text.atobin());end endtask
initial begin
check("",32'h00000000,32'h00000000,32'h00000000,32'h00000000);
check("123",32'h0000007b,32'h00000123,32'h00000053,32'h00000001);
check("-123",32'hffffff85,32'hfffffedd,32'hffffffad,32'hffffffff);
check("+123",32'h0000007b,32'h00000123,32'h00000053,32'h00000001);
check(" 123",32'h00000000,32'h00000000,32'h00000000,32'h00000000);
check("\t123",32'h00000000,32'h00000000,32'h00000000,32'h00000000);
check("__1_2__3",32'h0000007b,32'h00000123,32'h00000053,32'h00000001);
check("123foo",32'h0000007b,32'h0000123f,32'h00000053,32'h00000001);
check("0x12",32'h00000000,32'h00000012,32'h00000000,32'h00000000);
check("0b10",32'h00000000,32'h00000b10,32'h00000000,32'h00000002);
check("0o77",32'h00000000,32'h00000000,32'h0000003f,32'h00000000);
check("0Xf",32'h00000000,32'h00000000,32'h00000000,32'h00000000);
check("0O77",32'h00000000,32'h00000000,32'h00000000,32'h00000000);
check("0B11",32'h00000000,32'h00000b11,32'h00000000,32'h00000000);
check("ffffffff",32'h00000000,32'hffffffff,32'h00000000,32'h00000000);
check("100000000",32'h05f5e100,32'h00000000,32'h01000000,32'h00000100);
check("4294967296",32'h00000000,32'h94967296,32'h00000022,32'h00000000);
check("-2147483649",32'h7fffffff,32'hb8b7c9b7,32'hffffdcc4,32'h00000000);
check("-ff",32'h00000000,32'hffffff01,32'h00000000,32'h00000000);
check("7_7",32'h0000004d,32'h00000077,32'h0000003f,32'h00000000);
check("10xz",32'h0000000a,32'h00000010,32'h00000008,32'h00000002);
check("x1",32'h00000000,32'h00000000,32'h00000000,32'h00000000);
check("12.5",32'h0000000c,32'h00000012,32'h0000000a,32'h00000001);
check("_-12",32'hfffffff4,32'hffffffee,32'hfffffff6,32'hffffffff);
check("_0x_f",32'h00000000,32'h0000000f,32'h00000000,32'h00000000);
check("-0x20",32'h00000000,32'hffffffe0,32'h00000000,32'h00000000);
check("0_b10",32'h00000000,32'h00000b10,32'h00000000,32'h00000002);
check("12 3",32'h0000000c,32'h00000012,32'h0000000a,32'h00000001);
check("+-12",32'h00000000,32'h00000000,32'h00000000,32'h00000000);
check("18446744073709551616",32'h00000000,32'h09551616,32'h00000001,32'h00000001);
source="ffffffff";signed_result=source.atohex();
if(signed_result!=-1||!(source.atohex()<0)||$bits(source.atohex())!=32)$fatal(1,"signed conversion result");
$display("TRACE signed %0d %0d",signed_result,$bits(source.atohex()));
#1;$finish;end endmodule
