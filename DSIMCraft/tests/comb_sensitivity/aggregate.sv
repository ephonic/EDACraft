`timescale 1ns/1ps
module top;
typedef struct packed {logic [3:0] high;logic[3:0] low;} pair_t;
pair_t q;
logic [1:0][3:0] packed_q;
logic [7:0] mem[2];
logic [130:0] wide;
always_comb begin
 q.high=q.low;
 packed_q[1]=packed_q[0];
 mem[0][7:4]=mem[0][3:0];mem[1][7:4]=mem[1][3:0];
 wide[130:65]={wide[64:0],wide[0]};
end
initial begin
 #1;q.low=1;packed_q[0]=2;mem[0][3:0]=3;mem[1][3:0]=4;wide[64:0]=65'h1fffffffffffffffe;
 #1;$display("TRACE aggregate %b %b %b %b %b",q,packed_q,mem[0],mem[1],wide);
 q.low=4'hz;packed_q[0]=4'hx;mem[0][3:0]=4'hz;mem[1][3:0]=4'hx;wide[64:0]={1'bz,64'h8000000000000001};
 #1;$display("TRACE aggregate %b %b %b %b %b",q,packed_q,mem[0],mem[1],wide);$finish;
end
endmodule
