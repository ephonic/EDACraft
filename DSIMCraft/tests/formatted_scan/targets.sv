`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 int n,i,a[0:5];reg[31:0]packed_value;bit[7:0]byte_value;string s,fmt="%d%d";
 function automatic string stimulus();i++;return "7 8";endfunction
 initial begin
  for(i=0;i<6;i++)a[i]=100+i;
  #1;i=0;n=$sscanf("7 nope",fmt,a[i++],a[i++]);
  $display("TRACE ONE %0d %0d %0d %0d %0d %0d",n,i,a[0],a[1],a[2],a[3]);
  #1;i=0;n=$sscanf("8 9",fmt,a[i++],a[i++]);
  $display("TRACE TWO %0d %0d %0d %0d %0d %0d",n,i,a[0],a[1],a[2],a[3]);
  #1;i=0;n=$sscanf("",fmt,a[i++],a[i++]);$display("TRACE EMPTY %0d %0d",n,i);
  #1;i=0;n=$sscanf(stimulus(),fmt,a[i++],a[i++]);
  $display("TRACE EVAL %0d %0d %0d %0d",n,i,a[3],a[4]);
  #1;packed_value='1;n=$sscanf("abcd Q","%2s %c",packed_value[23:8],byte_value);
  $display("TRACE SLICE %0d %h %h",n,packed_value,byte_value);
  #1;n=$sscanf("x","%h",byte_value);$display("TRACE TWO_STATE %0d %h",n,byte_value);
  #1;n=$sscanf(" hello Q","%s %c",s,packed_value);$display("TRACE STR %0d <%s> %h",n,s,packed_value);
  #1;void'($sscanf("99","%d",n));$display("TRACE VOID %0d",n);
  #1;n=$sscanf("12345","%h",{packed_value[15:8],byte_value});$display("TRACE CONCAT %0d %h %h",n,packed_value,byte_value);
  #1;$finish;
 end
endmodule
