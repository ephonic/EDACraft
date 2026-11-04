`timescale 1ns/1ps
module unit #(parameter W=5)(output logic[31:0] result);
typedef logic[W-1:0] word_t;
typedef enum logic[2:0]{IDLE=0,GO=1} state_t;
typedef struct packed {state_t state;word_t data;} packet_t;
word_t data,mem[2:4];packet_t packet;
localparam B=$bits(packet_t), M=$bits(mem), A=$clog2(W), C=$countones({5'b10101,4'b1xz0});
localparam X=$clog2(4'b1x01), O=$onehot(4'b1xz0), Z=$onehot0(4'b0xz0);
logic[B-1:0] storage;
int touched=0;
function longint probe(input int value);
 begin probe=value+1;end
endfunction
initial begin
 result=B*10000+M*100+A*10+C;
 if(B!=W+3||M!=W*3||C!=4||X!==32'bx||O!==1||Z!==1)$fatal(1,"constant functions");
 if($bits(storage)!=B||$bits(mem[touched++])!=W||$bits(probe(touched++))!=64||touched!=0)$fatal(1,"unevaluated operand");
 if(probe(0)!=1)$fatal(1,"runtime function result");
 if($bits(int)!=32||$bits(byte)!=8||$bits(shortint)!=16||$bits(longint)!=64||$bits(integer)!=32||$bits(time)!=64)$fatal(1,"atom types");
 if($bits(logic signed[W-1:0])!=W||$bits(bit unsigned[0:W-1])!=W)$fatal(1,"packed type");
 if($bits(data+1)!=32||$bits(data<<64'b1)!=W||$bits(data==1)!=1||$bits({data,packet.state})!=B||$bits({3{data}})!=W*3)$fatal(1,"expression type");
 if($bits($countones(data))!=32||$bits($clog2(data))!=32||$bits($onehot(data))!=1||$bits($onehot0(data))!=1||$bits($isunknown(data))!=1)$fatal(1,"result type");
end
for(genvar g=0;g<2;g=g+1)begin:gen
 typedef logic[W+g-1:0] item_t;
 localparam N=$bits(item_t), L=$clog2(N);
 logic[N-1:0] q;
 initial begin
  q=N+L;
  if(N!=W+g||$bits(q)!=W+g)$fatal(1,"generate widths");
 end
end
endmodule
module top;
wire[31:0] a,b;
unit #(.W(5)) u(.result(a));unit #(.W(9)) v(.result(b));
initial begin #1;
 if(a!=81534||b!=122744)$fatal(1,"instance values %0d %0d",a,b);
 $display("TRACE constants %0d %0d",a,b);
end
endmodule
