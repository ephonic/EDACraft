`timescale 1ns/1ps
package header_types;
 parameter integer WIDTH=5;
 typedef logic [WIDTH-1:0] word_t;
 typedef enum logic[1:0] {IDLE=0,BUSY=2} state_t;
 function automatic word_t bump(input word_t x);return x+1;endfunction
endpackage
import header_types::*;
module lane
 #(parameter integer N=WIDTH,parameter word_t INIT=3)
 (input logic clk,input word_t value,output word_t next_value,output logic[N-1:0] saved);
 assign next_value=bump(value);
 always @(posedge clk) saved<=value+INIT;
endmodule
(* keep=1 *) module legacy (a,y);
 input [WIDTH-1:0] a;
 output word_t y;
 assign y=a^5'h1a;
endmodule
module top;
 logic clk=0;header_types::word_t value=5'h1f;
 wire[4:0] next_value,legacy_value;wire[6:0] saved;
 lane #(.N(7),.INIT(2)) u(clk,value,next_value,saved);
 legacy old(value,legacy_value);
 initial begin
  #1;clk=1;#1;
  if(next_value!==0||saved!==33||legacy_value!==5)$fatal(1,"header typedef/defaults/override");
  value=7;#1;clk=0;#1;clk=1;#1;
  if(next_value!==8||saved!==9||legacy_value!==29)$fatal(1,"header typed ports");
  $display("TRACE unit ports %h %h %h",next_value,saved,legacy_value);
 end
endmodule
