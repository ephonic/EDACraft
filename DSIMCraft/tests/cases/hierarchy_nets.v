module endpoint(input en, input d, inout bus, output seen);
  assign bus=en?d:1'bz;
  assign seen=bus;
endmodule
module readback(input en, input d, output bus, output seen);
  assign bus=en?d:1'bz;
  assign seen=bus;
endmodule
module shifted(input [7:4] a, output [9:6] y);
  assign y={a[7:6],a[5:4]};
endmodule
module top;
  reg en0,en1,d0,d1,ext_en,ext_d;
  wire bus,s0,s1,ob,os;
  wire [3:0] n=4'ha;
  wire [3:0] shifted_y;
  endpoint e0(en0,d0,bus,s0),e1(en1,d1,bus,s1);
  readback rb(en0,d0,ob,os);
  shifted sh(n,shifted_y);
  assign ob=ext_en?ext_d:1'bz;
  initial begin
    en0=0; en1=0; d0=0; d1=1; ext_en=1; ext_d=1;
    #1 $display("TRACE bus=%b seen=%b%b output=%b read=%b shift=%h",bus,s0,s1,ob,os,shifted_y);
    en0=1;
    #1 $display("TRACE bus=%b seen=%b%b output=%b read=%b",bus,s0,s1,ob,os);
    en1=1;
    #1 $display("TRACE bus=%b seen=%b%b",bus,s0,s1);
    en0=0;
    #1 $display("TRACE bus=%b seen=%b%b",bus,s0,s1);
    en1=0; ext_en=0;
    #1 $display("TRACE bus=%b seen=%b%b output=%b read=%b",bus,s0,s1,ob,os);
    $finish;
  end
endmodule
