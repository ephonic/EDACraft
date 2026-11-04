`timescale 1ns/1ps
package port_types;
 typedef logic signed [7:0] signed_t;
 typedef bit [3:0] bit_t;
 typedef struct packed {logic [3:0] hi;logic [3:0] lo;} record_t;
 typedef enum logic [1:0] {IDLE=0,BUSY=2} state_t;
endpackage
module typed import port_types::*;
 ((* keep=1 *) input signed_t a,b,input bit_t two,input record_t packet,input state_t state,
  output var record_t echo,output signed_t delta,output bit_t bit_echo);
 assign echo=packet;
 assign delta=a+b;
 assign bit_echo=two;
 initial begin
  #1;
  if(a!=-7||b!=2||state!=BUSY||packet.hi!=10||packet.lo!=5)
   $fatal(1,"named port type metadata");
 end
endmodule
module qualified(input port_types::signed_t a,output port_types::signed_t y);
 assign y=a+1;
endmodule
module top;
 port_types::signed_t a=-7,b=2;
 port_types::record_t packet=8'ha5;
 port_types::state_t state=port_types::BUSY;
 logic [3:0] two=4'b1xz0;
 wire [7:0] echo;
 wire signed [7:0] delta;
 wire signed [7:0] qualified_value;
 wire [3:0] bit_echo;
 typed u(a,b,two,packet,state,echo,delta,bit_echo);
 qualified q(a,qualified_value);
 initial begin
  #2;
  if(echo!==8'ha5||delta!=-5||bit_echo!==8||qualified_value!=-6)$fatal(1,"named output types");
  $display("TRACE header types %h %0d %h",echo,delta,bit_echo);
 end
endmodule
