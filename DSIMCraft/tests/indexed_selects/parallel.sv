`timescale 1ps/1ps
module island;
reg [79:0] q;
reg [6:0] i;
wire[7:0] part;
assign part=q[i+:8];
initial begin
 q=80'h123456789abcdef01234;i=0;
 // Sample after the continuous select settles, avoiding an Active-region race.
 repeat(8)begin #1;q[i+:8]<=#2 part^8'ha5;#3;i=i+9;end
end
endmodule
module top;
island a();island b();
endmodule
