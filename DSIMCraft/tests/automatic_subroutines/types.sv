`timescale 1ns/1ps
module top;
typedef logic signed[7:0] byte_t;
typedef bit[129:0] wide_t;
typedef enum logic[1:0]{A,B,C} state_t;
typedef struct packed{state_t state;byte_t data;bit valid;} packet_t;
byte_t narrow;wide_t wide;state_t state=A;packet_t packet;integer q=0,calls=0;
function automatic byte_t signed_copy(input byte_t x=-2,output byte_t y=narrow);
 byte_t local_value=x-1;
 begin y=local_value;return y;end
endfunction
function automatic wide_t clean(input wide_t x=130'h3fffffffffffffffffffffffffffffffx,output wide_t y=wide);
 wide_t local_value=x+1;
 begin y=local_value;return y;end
endfunction
function automatic state_t advance(input state_t x=B,output state_t y=state);
 begin if(x==B)y=C;else y=B;return y;end
endfunction
function automatic packet_t pack(input byte_t data=-5,input state_t phase=B,output packet_t y=packet);
 packet_t p=0;
 begin p.data=data;p.state=phase;p.valid=1;y=p;return y;end
endfunction
function automatic byte_t classic;input byte_t x;byte_t local_value=x+1;begin return local_value;end endfunction
function automatic void touch(input integer delta=1);begin calls+=delta;end endfunction
function automatic implicit_ansi(input integer x);begin return x;end endfunction
function automatic implicit_classic;input integer x;begin return x;end endfunction
function automatic implicit_block(input integer x);bit local_value=x;begin return local_value;end endfunction
function automatic[7:0] packed_result(input integer x);begin return x;end endfunction
function automatic[7:0] packed_classic;input integer x;begin return x;end endfunction
function automatic[7:0] packed_block(input integer x);logic[7:0] local_value=x;begin return local_value;end endfunction
function automatic byte byte_result(input integer x);begin return x;end endfunction
initial begin
 if(implicit_ansi(3)!==1'b1||implicit_classic(2)!==1'b0||implicit_block(3)!==1'b1)$fatal(1,"implicit return type");
 if(packed_result(511)!==8'hff||packed_classic(258)!==8'h02||packed_block(257)!==8'h01)$fatal(1,"packed return type");
 if(byte_result(255)!==-1)$fatal(1,"byte return type");
 q=signed_copy();if(q!==-3||narrow!==-3)$fatal(1,"signed lifetime");
 state=advance(.y());if(state!==C)$fatal(1,"enum automatic");
 wide=clean();if(wide!==130'h3fffffffffffffffffffffffffffffff1)$fatal(1,"wide two state");
 packet=pack(.phase(A));if(packet.state!==A||packet.data!==-5||packet.valid!==1)$fatal(1,"packed automatic");
 q=classic(-8);if(q!==-7)$fatal(1,"classic automatic");
 touch();touch(.delta(3));if(calls!==4)$fatal(1,"automatic void");
 #1 $display("TRACE types complete");
end
endmodule
