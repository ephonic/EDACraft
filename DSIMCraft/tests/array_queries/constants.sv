`timescale 1ns/1ps
module unit #(parameter W=5)(output logic[31:0] result);
typedef logic[W+2:3] word_t;
typedef logic scalar_t;
typedef logic[0:0] singleton_t;
typedef enum logic {IDLE=0,GO=1} state_t;
typedef struct packed {word_t data;logic flag;} packet_t;
word_t mem[2:6];packet_t packet;integer integers[5:3];
parameter logic SP=0;parameter[9:5] VP=0;parameter P=1'b0;
localparam D=$dimensions(mem), U=$unpacked_dimensions(mem), N=$size(mem,2);
localparam L=$left(word_t), R=$right(word_t), I=$increment(mem), J=$increment(integers);
localparam C=5;
localparam INV=$left(mem,3), H=32'bx;
logic[N-1:0] storage;
initial begin
 result=D*10000+U*1000+N*100+L*10+R;
 if($countbits({4'b01xz,4'b1010},1'bx,1'bz,1'b1,1'b1)!=C)$fatal(1,"constant operand runtime call");
 if(D!=2||U!=1||N!=W||L!=W+2||R!=3||I!=-1||J!=1||C!=5)$fatal(1,"elaboration");
 if(INV!==32'bx||H!==32'bx)$fatal(1,"invalid constant dimension");
 if($dimensions(scalar_t)!=0||$dimensions(singleton_t)!=1||$dimensions(state_t)!=1||$dimensions(packet_t)!=1)$fatal(1,"named type dimensions");
 if($dimensions(SP)!=0||$dimensions(VP)!=1||$dimensions(P)!=1||$left(VP)!=9||$right(VP)!=5)$fatal(1,"parameter shape");
 if($left(packet.data)!=W+2||$right(packet.data)!=3)$fatal(1,"member shape");
 if($dimensions(int)!=1||$dimensions(logic)!=0||$unpacked_dimensions(time)!=0||$size(byte)!=8||$left(longint)!=63||$right(shortint)!=0)$fatal(1,"builtin type");
 if($left(logic signed[3:-2])!=3||$right(logic signed[3:-2])!=-2||$low(bit[0:4])!=0||$high(bit[0:4])!=4||$increment(bit[0:4])!=-1)$fatal(1,"type range");
 if($dimensions(bit[0:0])!=1||$size(int,2)!==32'bx||$size(logic)!==32'bx)$fatal(1,"type boundaries");
 if($bits($left(mem))!=32||$bits($dimensions(mem))!=32||$bits($countbits(1'bx,1'bx))!=32||$bits(storage)!=W)$fatal(1,"result types");
end
for(genvar g=0;g<2;g=g+1)begin:gen
 typedef logic[W+g+2:3] item_t;
 localparam B=$size(item_t), K=$countones(g);
 logic[B-1:0] value;
 initial begin value=B+K;if(B!=W+g||$left(item_t)!=W+g+2||$right(item_t)!=3)$fatal(1,"generate binding");end
end
endmodule
module top;
wire[31:0] a,b;
unit #(.W(5)) u(.result(a));unit #(.W(9)) v(.result(b));
initial begin #1;if(a!=21573||b!=22013)$fatal(1,"instances %0d %0d",a,b);$display("TRACE constants %0d %0d",a,b);end
endmodule
