`timescale 1ns/1ps
module top;
 logic[7:0] a[]=new[2];integer calls=0;logic[15:0] observed=0;
 function automatic integer count();calls++;a[0]=8'b1xz001zx;a[1]=8'hcd;return 3;endfunction
`ifdef ELEMENTWISE_REFERENCE
 bit[7:0] b[]=new[count()];
`else
 bit[7:0] b[]=new[count()](a);
`endif
 logic[7:0] four[];integer integers[]=new[2];int ints[];
 logic[7:0] fixed_source[3:2];bit[7:0] from_fixed[];
 logic[95:0] wide[]=new[1];bit[95:0] bits[];
 initial begin
`ifdef ELEMENTWISE_REFERENCE
  foreach(b[i])if(i<a.size())b[i]=a[i];
`endif
  $display("TRACE constructor %0d %0d %h %h %h",calls,b.size(),b[0],b[1],b[2]);
  a[0]=0;
`ifdef ELEMENTWISE_REFERENCE
  four=new[4];foreach(four[i])if(i<b.size())four[i]=b[i];
`else
  four=new[4](b);
`endif
  $display("TRACE four %h %h %h %h",four[0],four[1],four[2],four[3]);
  integers[0]=32'hx1234567;integers[1]=-2;
`ifdef ELEMENTWISE_REFERENCE
  ints=new[3];foreach(ints[i])if(i<integers.size())ints[i]=integers[i];
`else
  ints=new[3](integers);
`endif
  $display("TRACE int %h %h %h",ints[0],ints[1],ints[2]);
  fixed_source[3]=8'b1xz001zx;fixed_source[2]=8'hff;
`ifdef ELEMENTWISE_REFERENCE
  from_fixed=new[3];from_fixed[0]=fixed_source[3];from_fixed[1]=fixed_source[2];
`else
  from_fixed=new[3](fixed_source);
`endif
  wide[0]=96'hx123456789abcdef00123456;
`ifdef ELEMENTWISE_REFERENCE
  bits=new[2];foreach(bits[i])if(i<wide.size())bits[i]=wide[i];
`else
  bits=new[2](wide);
`endif
  #1;observed={from_fixed[0],from_fixed[1]};
  $display("TRACE fixed_new %h %h %h",from_fixed[0],from_fixed[1],from_fixed[2]);
  $display("TRACE wide_new %h %h",bits[0],bits[1]);
 end
endmodule
