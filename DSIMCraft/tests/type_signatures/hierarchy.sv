`timescale 1ns/1ps
module lane;
parameter int W=4;
typedef logic signed[W+4:5] word_t;
typedef struct packed {word_t data;bit valid;} packet_t;
parameter word_t START=-2;
localparam packet_t INIT={START,1'b1};
localparam word_t COPY=INIT.data;
word_t q;packet_t p;
function word_t sum(input word_t x,input word_t y);
 begin sum=x+y;end
endfunction
genvar g;
generate for(g=0;g<2;g=g+1)begin: gen
 typedef bit[W+g-1:0] word_t;
 localparam word_t MASK='1;
 word_t q;
 function word_t clear_unknown(input word_t x);
  begin clear_unknown=x;end
 endfunction
 initial begin
  q=clear_unknown('x);if(q!==0||$bits(MASK)!=W+g||$size(MASK)!=W+g)$fatal(1,"generate type");
  #1 q=clear_unknown(MASK);if(q!==MASK)$fatal(1,"generate binding");
 end
end endgenerate
initial begin: body
 typedef bit[2:0] tiny_t;
 localparam tiny_t LOCAL=10;
 if(LOCAL!==2||$left(COPY)!=W+4||$right(COPY)!=5||$bits(INIT)!=W+1)$fatal(1,"parameter metadata");
 q=START;p=INIT;#1 q=sum(q,1);p.data=q;
 if(COPY!==START||q!==START+1||p.data!==q||p.valid!==1)$fatal(1,"instance binding");
end
endmodule
module top;
lane #(.W(4),.START(-3))u();
lane #(.W(9),.START(-6))v();
initial #3 $display("TRACE hierarchy complete");
endmodule
