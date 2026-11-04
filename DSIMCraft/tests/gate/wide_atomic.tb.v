module top;
reg [1:0] a; reg ready; reg [7:0] changes; wire y; dut u(a,y);
always @(y) if(ready) changes=changes+8'd1;
initial begin ready=0; changes=0; a=2'b01; #1; ready=1;
a=2'b10; #1; $display("TRACE a=%b y=%b changes=%0d",a,y,changes);
a=2'b00; #1; $display("TRACE a=%b y=%b changes=%0d",a,y,changes);
a=2'b11; #1; $display("TRACE a=%b y=%b changes=%0d",a,y,changes);
a=2'bxz; #1; $display("TRACE a=%b y=%b changes=%0d",a,y,changes);
a=2'bzz; #1; $display("TRACE a=%b y=%b changes=%0d",a,y,changes);
a=2'bx1; #1; $display("TRACE a=%b y=%b changes=%0d",a,y,changes);
$finish; end endmodule
