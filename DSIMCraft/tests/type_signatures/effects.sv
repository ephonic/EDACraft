`timescale 1ns/1ps
module top;
typedef logic signed[7:0] byte_t;
typedef bit[69:0] wide_t;
typedef enum logic[1:0] {IDLE,BUSY,DONE} state_t;
typedef struct packed {state_t state;byte_t data;bit valid;} packet_t;
byte_t a=1,b=-5;packet_t packet;state_t state=IDLE;wide_t wide;int calls=0;
function byte_t twice(input byte_t x);
 begin twice=x+x;end
endfunction
function state_t choose(input state_t x);
 begin if(x==IDLE)return BUSY;return DONE;end
endfunction
task change(input byte_t captured,output packet_t result,inout byte_t value);
 packet_t local_packet;
 begin
  local_packet=0;local_packet.state=BUSY;local_packet.data=captured;local_packet.valid=1;
  #2 value=value+captured;result=local_packet;result.data=value;
 end
endtask
task phase;
 input state_t x;
 output state_t y;
 begin #1 y=choose(x);end
endtask
task scrub(input wide_t x,output wide_t y);
 begin y=x+1;end
endtask
initial begin
 change(twice(a++),packet,b);calls=a;
 if(a!==2||calls!==2||b!==-3||packet.data!==-3||packet.state!==BUSY||packet.valid!==1)$fatal(1,"typed task copy");
 phase(state,state);if(state!==BUSY)$fatal(1,"enum copyout");
 phase(state,state);if(state!==DONE)$fatal(1,"enum inout actual");
 scrub(70'h3ffffffffffffffffx,wide);if(wide!==70'h3ffffffffffffffff1)$fatal(1,"two state task");
 packet.data<=#2 twice(b++);#1 if(b!==-2)$fatal(1,"nba rhs once");
 #2 if(packet.data!==-6)$fatal(1,"nba typed function");
 $display("TRACE effects complete");
end
endmodule
