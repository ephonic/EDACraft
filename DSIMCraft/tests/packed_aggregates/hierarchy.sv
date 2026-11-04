`timescale 1ns/1ps
module tap #(parameter int W=3)(input logic[W-1:0] a,output wire[W:0] y);
assign y={1'b0,a}+1;
endmodule
module lane #(parameter int W=3);
typedef struct packed {logic[W-1:0] data;bit valid;} packet_t;
typedef packet_t alias_t;
alias_t packet;
wire[W:0] observed;
tap #(.W(W))t(packet.data,observed);
genvar g;
generate for(g=0;g<2;g=g+1)begin: gen
 typedef struct packed {bit[W+g-1:0] a;bit[W+g-1:0] b;} pair_t;
 pair_t x;
 initial begin
  x=0;x.a=W+g;x.b=1;
  #1 x.a++;
  #1 if(x.a!==(W+g+1)||x.b!==1)$fatal(1,"generate layout");
 end
end endgenerate
function integer local_sum;
 input integer a;
 typedef struct packed {bit[W-1:0] data;bit valid;} local_t;
 local_t v;
 v=0;v.data=a;v.valid=1;local_sum=v.data+v.valid;
endfunction
initial begin: body
 typedef struct packed {bit[1:0] data;bit valid;} packet_t;
 packet_t local_packet;
 local_packet=0;local_packet.data=2;local_packet.valid=1;
 if(local_packet!==3'b101)$fatal(1,"local shadow");
 packet=0;packet.data=W;packet.valid=1;
 #2 if(packet.data!==W||packet.valid!==1||local_sum(packet.data)!==W+1||observed!==W+1)$fatal(1,"scopes");
end
endmodule
module top;
lane #(.W(3))u();lane #(.W(7))v();
initial #4 $display("TRACE hierarchy complete");
endmodule
