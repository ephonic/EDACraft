`timescale 1ns/1ps
module top;
typedef enum logic [7:0] {A=8'hf0,B,C} outer_t;
outer_t out;
logic [7:0] result;
function [7:0] convert(input reg [7:0] x);
 typedef enum logic [7:0] {A=8'd3,B,C} local_t;
 local_t q;
 q=local_t'(x);q++;convert=q;
endfunction
task choose(output reg [7:0] x);
 typedef enum bit [7:0] {T=8'd17,U} task_t;
 task_t q;
 q=U;x=q;
endtask
initial begin
 out=A;
 begin: nested
  typedef enum logic signed [12:0] {A=-2,B,C=5,D} inner_t;
  typedef inner_t alias_t;
  inner_t q;alias_t copy;
  q=A;copy=1?B:C;q++;
  if(q!==B||copy!==B||q!==13'h1fff)$fatal(1,"local shadow");
  #1 $display("TRACE nested %h %h",q,copy);
 end
 result=convert(8'hff);if(result!==8'h00||out!==8'hf0)$fatal(1,"function enum");
 choose(result);if(result!==8'd18)$fatal(1,"task enum");
 #1 $display("TRACE scopes %h %h",out,result);
end
endmodule
