`timescale 1ns/1ps
module top;
typedef logic signed[7:0] byte_t;
typedef bit[69:0] wide_t;
typedef enum logic[1:0]{IDLE,BUSY,DONE} state_t;
typedef struct packed{state_t state;byte_t data;bit valid;} packet_t;
byte_t narrow;wide_t wide;state_t state=IDLE;packet_t packet;integer q;
function byte_t signed_copy(input byte_t x=-2,output byte_t y=narrow);
 begin y=x-1;return y;end
endfunction
function state_t advance(input state_t x=BUSY,output state_t y=state);
 begin if(x==BUSY)y=DONE;else y=BUSY;return y;end
endfunction
function wide_t clean(input wide_t x=70'h3ffffffffffffffffx,output wide_t y=wide);
 begin y=x+1;return y;end
endfunction
function packet_t pack(input byte_t data=-5,input state_t phase=BUSY,output packet_t y=packet);
 begin y=0;y.state=phase;y.data=data;y.valid=1;return y;end
endfunction
generate for(genvar g=0;g<2;g=g+1)begin:lanes
 localparam integer BASE=g+4;
 integer result;
 function byte_t get(input byte_t x=BASE);begin return x;end endfunction
 initial begin #1 result=get();if(result!==BASE)$fatal(1,"generate default scope");end
end endgenerate
initial begin
 q=signed_copy();if(q!==-3||narrow!==-3)$fatal(1,"signed default");
 state=advance(.y());if(state!==DONE)$fatal(1,"enum default");
 wide=clean();if(wide!==70'h3ffffffffffffffff1)$fatal(1,"wide two state default");
 packet=pack(.phase(IDLE));if(packet.state!==IDLE||packet.data!==-5||packet.valid!==1)$fatal(1,"packed named defaults");
 #2 $display("TRACE types complete");
end
endmodule
