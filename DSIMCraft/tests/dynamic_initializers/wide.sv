`timescale 1ns/1ps
module top;
 logic signed[95:0] src[]=new[2];
 integer fixed_src[3:1];integer result=0;
 initial begin
  src[0]=96'h123456789abcdef001234567;src[1]=96'hfedcba987654321001234567;
  fixed_src[3]=11;fixed_src[2]=22;fixed_src[1]=33;
  begin : copies
   automatic logic signed[95:0] a[]=new[3](src),b[]=a;
   automatic bit[95:0] zeros[]=new[2];
   automatic integer f[]=fixed_src,g[]=new[5](fixed_src);
   a[0][7:0]=8'hab;src[1]=0;
   $display("TRACE wide %h %h %h %h %h",a[0],b[0],b[1],a[2],zeros[1]);
   $display("TRACE fixed %0d %0d %0d %0d %0d %h",f.size(),f[0],f[1],f[2],g.size(),g[4]);
   #1;result=f[0]+f[1]+f[2]+g[2];
  end
 end
endmodule
