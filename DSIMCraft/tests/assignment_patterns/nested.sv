`timescale 1ns/1ps
module top;
 localparam N=2;
 integer a[0:1][3:2]='{'{1,2},'{3,4}};
 logic signed[7:0] neg[1:0];
 bit[1:0][39:0] wide;
 logic[-1:-2][3:0] negative_dims;
 initial begin
  negative_dims='{-1:4'hd,-2:4'h6};
  neg='{1:8'hfe,0:8'h83};
  wide='{40'h123456789a,40'hbcdef01234};
  #1;$display("TRACE nested %0d %0d %0d %0d %0d %0d %h %h",a[0][3],a[0][2],a[1][3],a[1][2],neg[1],neg[0],wide,negative_dims);
  a='{default:'{default:7}};
  #1;$display("TRACE default %0d %0d %0d %0d",a[0][3],a[0][2],a[1][3],a[1][2]);
  a='{N{'{2{11}}}};
  wide='{default:'1};
  #1;$display("TRACE repeat2 %0d %0d %0d %0d %h %h",a[0][3],a[0][2],a[1][3],a[1][2],wide,negative_dims);
 end
endmodule
