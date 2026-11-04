`timescale 1ps/1ps
module island;
logic clk, reset_n, en;
logic [7:0] d,q,held,mixed;
initial begin clk=0;reset_n=0;en=0;d=1;
  #1;reset_n=1;en=1;
  repeat(5) begin #2;clk=1;#2;clk=0;d=d+3;en=~en;end
end
always_ff @(posedge clk or negedge reset_n) if(!reset_n)q<=0;else q<=d;
always_latch if(en)held=d;
always_comb mixed=q^held;
endmodule
module top;
island a();
island b();
endmodule
