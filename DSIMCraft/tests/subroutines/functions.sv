`timescale 1ns/1ps
module top;
integer bias=3;
reg signed [7:0] a=-8'sd3;
reg [79:0] b=80'h0123456789abcdef0123;
wire [79:0] y;
integer z;
function integer fold(input integer x);
 integer sum;
 begin
  sum=0;
  for(int k=0;k<6;k++)begin
   if(k==1)continue;
   if(k==5)break;
   sum=sum+x+k;
  end
  case(x)
   -3:fold=sum+bias;
   default:fold=sum-bias;
  endcase
 end
endfunction
function signed [79:0] mix(input signed [7:0] x,input [79:0] v);
 begin mix=$signed(v)+fold(x);end
endfunction
function parity(input [7:0] v);
 begin parity=^v;end
endfunction
assign y=mix(a,b);
always_comb z=fold(a);
initial begin
 #1;$display("TRACE fn %h %0d %b",y,z,parity(a));
 bias=9;#1;$display("TRACE bias %h %0d",y,z);
 a=4;b=80'hfffffffffffffffffff0;#1;$display("TRACE fn %h %0d %b",y,z,parity(a));
 a=8'bx01;#1;$display("TRACE unknown %h %h",y,z);
 $finish;
end
endmodule
