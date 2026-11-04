`timescale 1ns/1ps
module lane #(parameter int STEP=2,parameter int BASE=3)(output logic[15:0] q,output logic error);
typedef bit[15:0] word_t;
typedef struct packed {word_t count;bit valid;} packet_t;
localparam packet_t INIT=(BASE<<1)|1;
packet_t p;
function word_t add(input packet_t x,input word_t amount);
 begin add=x.count+amount;end
endfunction
task tick(input word_t x,output word_t y);
 begin #1 y=x+1;end
endtask
word_t temp;integer i;
initial begin
 q=0;error=0;p=INIT;temp=add(p,0);
 for(i=0;i<5;i=i+1)begin
  #(STEP) tick(add(p,2),temp);p.count=temp;q=temp;
  if(q!==BASE+(i+1)*3||p.valid!==1)error=1;
 end
end
endmodule
module top;
wire[15:0] a,b;wire ea,eb;
lane #(.STEP(2),.BASE(3))u(a,ea);
lane #(.STEP(3),.BASE(17))v(b,eb);
endmodule
