`timescale 1ns/1ps
module top;
 logic[7:0] a[]=new[2];bit[7:0] b[]=a;logic[7:0] c[]=b;
 logic signed[95:0] wide[]=new[2];bit signed[95:0] bits[];logic signed[95:0] back[];
 logic[95:0] observed=0;integer total=0;
 initial begin
  $display("TRACE startup %0d %h %h",b.size(),b[0],c[1]);
  a[0]=8'b1xz001zx;a[1]=8'hff;b=a;c=b;a[0]=9;
  $display("TRACE copy %h %h %h %h",b[0],b[1],c[0],a[0]);
  wide[0]=96'hx0123456789abcdef0012345;wide[1]=96'habcdef987654321011234567;
  bits=wide;back=bits;observed=back[0];total=b[0]+b[1];
  $display("TRACE wide %h %h %0d",bits[0],back[1],wide[0]===96'hx0123456789abcdef0012345);
  #1;b.delete();b=c;c[0]=1;total=b[0]+b[1];
  $display("TRACE independent %h %h %0d",b[0],c[0],total);
 end
endmodule
