`timescale 1ns/1ps
package alpha;
 parameter int W=12;
 localparam int BIAS=3;
 typedef logic[W-1:0] word_t;
 typedef enum logic[1:0] {IDLE=0, RUN=2, DONE=3} state_t;
 typedef struct packed {word_t data;state_t state;} packet_t;
endpackage : alpha
package beta;
 import alpha::word_t;
 typedef word_t other_t;
 parameter int W=7;
 typedef enum logic[1:0] {IDLE=1, RUN=3} state_t;
endpackage
module top;
 import alpha::word_t, alpha::packet_t;
 word_t data;
 packet_t packet;
 beta::other_t copy;
 alpha :: state_t state;
 logic[alpha::W-1:0] bits;
 integer result;
 initial begin
  data=12'habc;copy=data;state=alpha::RUN;
  packet='{data:data,state:state};bits=copy;
  if($bits(alpha::packet_t)!=14||$bits(beta::other_t)!=12||packet.data!==12'habc||packet.state!==alpha::RUN||bits!==data)$fatal(1,"package type layout");
  result=alpha::W+beta::W+alpha::BIAS+int'(beta::IDLE);
  #1;if(result!=23)$fatal(1,"qualified constants");
  $display("TRACE package namespaces %0h %0h %0d",packet,bits,result);
 end
endmodule
