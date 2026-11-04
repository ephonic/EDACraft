`timescale 1ns/1ps
package base;
 parameter int W=5;
 typedef logic signed[W-1:0] word_t;
 typedef enum logic[1:0] {IDLE=0,BUSY=2,DONE=3} state_t;
 typedef struct packed {state_t state;word_t data;} packet_t;
endpackage
package competing;parameter int W=9;endpackage
package api;
 import base::*;
 import competing::*;
 export base::W,base::word_t,base::packet_t,base::state_t,base::BUSY,base::DONE;
 export base::word_t;
endpackage
module lane import api::*; #(parameter N=W)(input word_t value,output logic[N-1:0] result);
 assign result=value;
endmodule
module top;
 import api::*;
 packet_t packet;
 word_t value;
 state_t state;
 logic[W-1:0] result;
 lane u(value,result);
 initial begin
  packet='0;value=-3;state=BUSY;packet.state=state;packet.data=value;
  #1;if(W!=5||$bits(packet)!=7||packet.data!=-3||result!=5'b11101)$fatal(1,"exported types");
  value=7;state=DONE;packet.state=state;packet.data=value;
  #1;if(result!=7||packet.state!=DONE)$fatal(1,"exported values");
  $display("TRACE export types %0d %0d %0d %0d",W,$bits(packet),packet.data,state);
 end
endmodule
