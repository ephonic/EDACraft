`timescale 1ns/1ps
module tb;
  reg clk=0;
  reg [7:0] c=0,source=8'd20,other=8'd31;
  wire [7:0] net_value=source+1;
  always #5 clk=~clk;
  always @(posedge clk)c<=c+1;
  initial begin
    #6;force c=source;#1;if(c!==20)$fatal(1,"force initial");
    source=21;#1;if(c!==21)$fatal(1,"force reactive");
    force c=other;source=33;#1;if(c!==31)$fatal(1,"force replacement");
    other=42;#1;if(c!==42)$fatal(1,"force second RHS");
    #6;if(c!==42)$fatal(1,"NBA overwrote force");
    release c;#1;if(c!==42)$fatal(1,"release variable hold");
    #9;if(c!==43)$fatal(1,"release variable resume");
    force net_value=8'd99;source=44;#1;if(net_value!==99)$fatal(1,"force net hold");
    release net_value;#1;if(net_value!==45)$fatal(1,"net release resolution");
    $display("TRACE force %0d %0d",c,net_value);$finish;
  end
endmodule
