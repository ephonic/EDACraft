`timescale 1ns/1ps
module top;
typedef enum {IDLE,RUN=4,DONE,NEG=-2,TAIL} state_t;
typedef state_t alias_t;
typedef enum logic signed [7:0] {S_MIN=8'h80,S_NEG=8'hff,S_ZERO,S_ONE} small_t;
typedef enum logic [3:0] {EX=4'bx01z,EZ=4'bz10x,E1=1,E2,E7=7} four_t;
typedef enum bit [129:0] {W0=130'h0ffffffffffffffff,W1,W2} wide_t;
typedef enum logic [3:0] {NARROW=2'd2,NEXT} narrow_t;
localparam CHOSEN=RUN;
localparam [129:0] WV=W1;
state_t state,old,mem[0:1];alias_t copy;small_t sm;four_t four;wide_t wide;narrow_t narrow;
int index=0;
logic [63:0] signed_value;
initial begin
 if(state!==IDLE||four!==4'bxxxx||wide!==130'b0) $fatal(1,"defaults");
 state=CHOSEN;copy=DONE;old=state++;mem[0]=old;mem[1]=++state;
 if(old!==RUN||state!==state_t'(6)||mem[0]!==RUN||mem[1]!==state_t'(6))$fatal(1,"updates");
 state=alias_t'(index++);copy=1?state:RUN;
 if(index!=1||state!==IDLE||copy!==IDLE)$fatal(1,"cast effects");
 sm=S_NEG;signed_value=sm;sm++;
 if(signed_value!==64'hffffffffffffffff||sm!==S_ZERO)$fatal(1,"signed");
 four=EX;if(four!==4'bx01z)$fatal(1,"X label");
 four=EZ;if(four!==4'bz10x)$fatal(1,"Z label");
 wide=W1;wide++;narrow=NEXT;
 if(wide!==W2||WV!==130'h10000000000000000||narrow!==4'd3)$fatal(1,"wide labels");
 mem[1] <= #2 NEG;
 #1 four=four_t'(4'bz0x1);
 #2 if(mem[1]!==NEG)$fatal(1,"delayed NBA");
 $display("TRACE values %0d %0d %h %b %h %h",state,index,signed_value,four,wide,narrow);
end
endmodule
