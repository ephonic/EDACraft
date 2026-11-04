`timescale 1ns/1ps
module top;
typedef logic signed [7:0] word_t;
word_t outer;
function [63:0] convert(input reg [31:0] value);
 typedef longint wide_t;
 wide_t temp;
 temp=wide_t'(value+1);
 convert=temp;
endfunction
task emit_value(output reg [7:0] result);
 typedef bit [7:0] byte_t;
 byte_t temp;
 temp=byte_t'(8'hxz);
 result=temp;
endtask
reg [63:0] answer;
reg [7:0] result;
initial begin: run
 typedef word_t local_t;
 local_t a;
 a=local_t'(128);outer=a;
 begin: nested
  typedef bit [12:0] word_t;
  word_t a,b;
  a=word_t'(16'hx5z1);b=word_t'(16'hffff);
  if(a!==13'h501||b!==13'h1fff) $fatal(1,"shadowed alias");
  #1;a=word_t'(9);$display("TRACE nested %h %h",a,b);
 end
 a=local_t'(255);answer=convert(32'hffffffff);emit_value(result);
 if(answer!==64'h100000000 || result!==0 || 64'(a)!==64'hffffffffffffffff) $fatal(1,"local aliases");
 #1;$display("TRACE scopes %h %h %h %h",outer,a,answer,result);$finish;
end
endmodule
