`timescale 1ns/1ps
module top;
logic [31:0] a;logic[4:0] sh;logic sel;
wire [31:0] mixed=sel?($signed(a)>>>sh):(a>>sh);
wire [31:0] both_signed=sel?($signed(a)>>>sh):$signed(a>>sh);
wire [31:0] separate_sra=$signed(a)>>>sh;
wire [31:0] via_wire=sel?separate_sra:(a>>sh);
wire [31:0] outside_cast=$signed(sel?($signed(a)>>>sh):(a>>sh));
initial begin
 a=32'hfffffffe;sh=10;sel=1;
 #1;if(mixed!==32'h003fffff||both_signed!==32'hffffffff||via_wire!==32'hffffffff||outside_cast!==32'h003fffff)$fatal(1,"signed context");
 $display("TRACE shift %h %h %h %h",mixed,both_signed,via_wire,outside_cast);
 sel=0;
 #1;$display("TRACE shift %h %h %h %h",mixed,both_signed,via_wire,outside_cast);
 sel=1'bx;
 #1;$display("TRACE shift-x %b %b %b %b",mixed,both_signed,via_wire,outside_cast);
 a=32'h80000000;sh=31;sel=1;
 #1;if(mixed!==1||both_signed!==32'hffffffff||via_wire!==32'hffffffff)$fatal(1,"shift 31");
 $display("TRACE shift %h %h %h %h",mixed,both_signed,via_wire,outside_cast);
 sh=0;
 #1;$display("TRACE shift %h %h %h %h",mixed,both_signed,via_wire,outside_cast);
 a=32'h7fffffff;sh=31;
 #1;$display("TRACE shift %h %h %h %h",mixed,both_signed,via_wire,outside_cast);$finish;
end
endmodule
