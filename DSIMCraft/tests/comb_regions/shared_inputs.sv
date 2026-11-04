`timescale 1ns/1ps
module top;
logic signed [7:0] a=1,b=-1;
logic rewrite=0;
integer observations=0;
wire signed [15:0] sum=$signed(a)+$signed(b),difference=$signed(a)-$signed(b);
wire [7:0] bitxor=a^b,bitand=a&b,bitor=a|b;
wire equal=(a===b),less=($signed(a)<$signed(b));
wire [15:0] joined={a,b};
wire [7:0] selected=a[b[2:0]] ? b : a;
// A queued observer may rewrite an input after a cohort, but never during it.
always @(bitxor) begin
 observations=observations+1;
 if(rewrite)begin rewrite=0;a=8'hf9;end
end
always @(sum) $display("TRACE shared %h %h %h %h %h %h %b %b %h",a,b,sum,difference,bitxor,bitand,equal,less,joined);
initial begin
 #1;a<=8'h80;b<=8'h03;a<=8'hfd;
 #1;if(sum!==16'h0000||difference!==16'hfffa||bitxor!==8'hfe||less!==1'b1)$fatal(1,"signed shared inputs");
 a=8'hxz;#0;b=8'hzz;
 #1;if(selected!==8'hxx)$fatal(1,"ambiguous conditional Z merge");
 a=8'h01;b=8'h01;
 #1;rewrite=1;a=8'h06;b=8'h02;
 #1;if(a!==8'hf9||sum!==16'hfffb||difference!==16'hfff7||joined!==16'hf902)$fatal(1,"observer rewrite boundary");
 a<=8'hff;b<=8'hff;b<=8'h00;
 #1;if(sum!==16'hffff||difference!==16'hffff||equal!==1'b0||selected!==8'h00)$fatal(1,"repeated NBA shared inputs");
 $display("TRACE shared done %0d %h %h %h",observations,sum,bitor,selected);
end
endmodule
