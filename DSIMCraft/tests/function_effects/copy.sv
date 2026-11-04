`timescale 1ns/1ps
module top;
integer data[0:3];integer idx=0,result=0,calls=0,total=0;
typedef logic signed[7:0] byte_t;
typedef bit[69:0] wide_t;
typedef enum logic[1:0]{IDLE,BUSY,DONE} state_t;
typedef struct packed{state_t state;byte_t data;bit valid;} packet_t;
byte_t narrow=-5;wide_t wide;state_t state=IDLE;packet_t packet;
function integer calc(input integer a,output integer out,inout integer io);
 begin calls++;idx=2;out=a+10;io=io+100;total+=3;return 7;end
endfunction
function void wrap(input integer a);
 begin total+=a;return;end
endfunction
function byte_t change(input byte_t x,output packet_t p,inout byte_t b);
 begin b=b+x;p=0;p.state=BUSY;p.data=b;p.valid=1;return b;end
endfunction
function state_t phase;
 input state_t x;
 output state_t y;
 begin if(x==IDLE)begin y=BUSY;return BUSY;end y=DONE;return DONE;end
endfunction
function wide_t clean(input wide_t x,output wide_t y);
 begin y=x+1;return y;end
endfunction
function void nested(input integer x);
 begin wrap(x);void'(calc(0,data[3],data[1]));end
endfunction
function integer identity(input integer x);begin return x;end endfunction
initial begin
 data[0]=1;data[1]=2;data[2]=3;data[3]=4;
 result=identity(calc(5,data[idx++],data[1]));
 if(result!==7||idx!==3||data[0]!==1||data[1]!==102||data[2]!==15||calls!==1||total!==3)$fatal(1,"copy address at return");
 wrap(4);void'(calc(1,data[0],data[1]));
 if(total!==10||calls!==2||data[0]!==11||data[1]!==202)$fatal(1,"discard copyout");
 #1 result=change(2,packet,narrow);
 if(result!==-3||narrow!==-3||packet.state!==BUSY||packet.data!==-3||packet.valid!==1)$fatal(1,"signed aggregate output");
 result=phase(state,state);if(result!==BUSY||state!==BUSY)$fatal(1,"early return copyout");
 void'(phase(state,state));if(state!==DONE)$fatal(1,"enum output");
 wide=clean(70'h3ffffffffffffffffx,wide);if(wide!==70'h3ffffffffffffffff1)$fatal(1,"wide two state output");
 #1 nested(5);calc(0,data[0],data[1]);
 if(total!==21||calls!==4||data[0]!==10||data[1]!==402||data[3]!==10)$fatal(1,"nested statement functions");
 $display("TRACE copy complete");
end
endmodule
