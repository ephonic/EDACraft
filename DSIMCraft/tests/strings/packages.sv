`timescale 1ns/1ps
package p;
 typedef enum logic[3:0]{OFF=0,ON=5,EX=4'bx101,EZ=4'bz101} state_t;
 typedef struct packed{logic[1:0] tag;state_t state;} packet_t;
 typedef string text_t;
 function automatic integer measure(input state_t state);
  string local_text;local_text=state.name();return local_text.len();
 endfunction
endpackage
module top;
 import p::*; packet_t packet; text_t label;integer size=0;reg valid=0;
 initial begin
  #0.25;packet='{tag:2,state:ON};label=packet.state.name;
  if(label!="ON"||measure(EX)!=2) $fatal(1,"package or packed field enum");
  packet.state=EZ;label=packet.state.name();size=label.len();valid=label=="EZ";
  $display("TRACE packages [%s] %0d %0d",label,size,valid);#0.25;$finish;
 end
endmodule
