`timescale 1ns/1ps
module top;
typedef logic signed[12:5] byte_t;
typedef bit[129:0] wide_t;
typedef logic singleton_t;
typedef enum logic[2:0] {IDLE=1,BUSY=3,DONE=5} state_t;
typedef state_t state_alias_t;
typedef struct packed {state_t state;byte_t data;bit valid;} packet_t;
typedef packet_t packet_alias_t;
typedef struct packed {bit[7:0] high;bit[63:0] low;} binary_packet_t;
typedef union packed {logic[11:0] raw;packet_t packet;} overlay_t;
localparam byte_t NEG=-2, EXT=NEG+1;
parameter wide_t CLEAN=130'h3fffffffffffffffffffffffffffffffxz;
localparam state_alias_t INIT=BUSY;
localparam packet_t PACK=12'h37d, MIX=12'bzxxxxxxxxxxx;
localparam binary_packet_t ZERO='x;
localparam state_t LABEL=PACK.state, EXPLICIT=state_t'(3);
localparam byte_t DATA=PACK.data;
localparam overlay_t OVER=PACK;
localparam integer WIDTH=$bits(PACK), LEFT=$left(NEG), RIGHT=$right(NEG);
byte_t a,b,c;wide_t w;state_t state;packet_t packet;overlay_t overlay;
logic signed[31:0] extended;logic bit_result;
function byte_t plus(input byte_t x,input byte_t y);
 begin
  if($left(x)!=12||$right(x)!=5||$size(x)!=8)plus=100;else plus=x+y;
 end
endfunction
function byte_t classic;
 input byte_t x,y;
 begin classic=x-y;end
endfunction
function state_alias_t next(input state_alias_t x);
 begin if(x==IDLE)return BUSY;next=DONE;end
endfunction
function packet_alias_t update(input packet_alias_t x,input byte_t delta);
 packet_t temp;
 begin temp=x;temp.data=temp.data+delta;temp.state=DONE;return temp;end
endfunction
function packet_t copy_packet(input packet_t x);
 begin return x;end
endfunction
function binary_packet_t clean_packet(input binary_packet_t x);
 begin return x;end
endfunction
function wide_t clean(input wide_t x);
 begin clean=x;end
endfunction
function singleton_t invert(input singleton_t x);
 begin invert=~x;end
endfunction
initial begin
 if(NEG!==-2||EXT!==-1||DATA!==-66||WIDTH!=12||LEFT!=12||RIGHT!=5||INIT!=BUSY||OVER.packet.data!==DATA)$fatal(1,"typed constants");
 if((CLEAN & 3)!==0||$bits(CLEAN)!=130)$fatal(1,"two state constant");
 packet=copy_packet(MIX);
 if(packet!==MIX||packet.valid!==0||packet.data!==8'bx||ZERO!==0||clean_packet('z)!==0)$fatal(1,"mixed and binary aggregate signatures");
 if(LABEL!==IDLE||EXPLICIT!==BUSY)$fatal(1,"enum parameter member and cast");
 a=NEG;b=3;c=plus(a,b);extended=classic(a,b);
 if(c!==1||extended!==-5)$fatal(1,"signed conversion");
 extended=plus(8'hfe,8'hff);
 if(extended!==-3)$fatal(1,"signed return extension");
 if(plus(plus(-2,1),plus(2,-1))!==0)$fatal(1,"nested typed calls");
 state=next(IDLE);if(state!==BUSY)$fatal(1,"enum return");
 state=next(state);if(state!==DONE)$fatal(1,"enum formal");
 packet=update(PACK,2);overlay=packet;
 if(packet.data!==-64||packet.state!==DONE||packet.valid!==1||overlay.raw!==12'hb81)$fatal(1,"packed signature");
 w=clean(130'h3fffffffffffffffffffffffffffffffxz);
 if(w[129:64]!==66'h3ffffffffffffffff||w[7:0]!==0)$fatal(1,"wide conversion");
 bit_result=invert(1'bx);if(bit_result!==1'bx)$fatal(1,"scalar four state");
 #1 packet.data<=#2 plus(packet.data,1);
 #3 if(packet.data!==-63)$fatal(1,"delay nba");
 $display("TRACE values complete");
end
endmodule
