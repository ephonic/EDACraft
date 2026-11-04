`timescale 1ns/1ps
module top;
logic clk=0,rst_n=0,enable=0,select=0;
logic [31:0] a=1,b=3,q=0,shadow=0;
integer accepted=0,loop_sum=0,j;
always #5 clk=~clk;
always_ff @(posedge clk or negedge rst_n) begin
 if(!rst_n) begin q<=0;shadow<=0;accepted<=0;end
 else if(enable) begin
  if(select) q<=a+b;else q<=q^b;
  shadow<=q;accepted<=accepted+1;
 end else if(select) begin shadow<=q+1;q<=32'hffffffff;end
 else begin shadow<=q;q<=a;end
end
// A loop retains the ordinary PC path; it shares the same notification FIFO.
always @(posedge clk) begin
 for(j=0;j<3;j++) loop_sum=loop_sum+j;
end
initial begin
 #2;rst_n=1;
 #9;enable=1;select=1;a=5;b=7;
 #10;select=0;b=32'h80000001;
 #10;enable=1'bx;select=1;
 #10;enable=0;select=0;a=32'hxxxxxxxx;
 #10;rst_n=0;
 #2;rst_n=1;enable=1;select=0;b=9;
 #10;select=1;a=7;
 #10;enable=0;select=1;
 #10;enable=0;select=0;a=123;
 #10;$display("TRACE branches %h %h %0d %0d",q,shadow,accepted,loop_sum);$finish;
end
endmodule
