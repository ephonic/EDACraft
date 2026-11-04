module top;
 typedef struct packed {enum logic[1:0]{IDLE,RUN,DONE} state;logic[5:0] data;} packet_t;
 packet_t packet;
 int observed;
 initial begin
  packet.state=packet.state.first();packet.state++;packet.data=6'h2a;
  if(packet.state.name()!="RUN"||packet!==8'h6a)$fatal(1,"packed anonymous enum");
  observed=packet;
  #1;$display("TRACE packed %h %s",packet,packet.state.name());$finish;
 end
endmodule
