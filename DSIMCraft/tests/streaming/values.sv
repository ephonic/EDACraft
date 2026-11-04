`timescale 1ns/1ps
module top;
 typedef logic[7:0] octet;
 localparam SLICE=4;
 localparam [23:0] CONST={<<8{16'h1234}};
 logic[9:0] x=10'b1011001101,y,z;
 logic[23:0] longer={<<byte{16'h1234}};
 logic[31:0] reverse_bits,reverse_bytes,nested,multiple;
 logic[7:0] first,second;
 logic[63:0] word64=64'hx123456789abcdef,edge_full,edge_partial;
 initial begin
  edge_full={<<64{word64}};edge_partial={<<7{word64}};
  y={<<SLICE{x}};z={>>4{x}};
  reverse_bits={<<{32'h01234567}};
  reverse_bytes={<<octet{32'h01234567}};
  nested={<<8{{<<4{32'h12345678}}}};
  multiple={>>{8'h12,16'h3456,8'h78}};
  #1;$display("TRACE values %b %b %h %h %h %h %h %h",y,z,longer,CONST,reverse_bits,reverse_bytes,nested,multiple);
  $display("TRACE edge %h %b",edge_full,edge_partial);
  {<<4{y}}=16'habcd;
  {<<8{reverse_bytes[15:0]}}=16'hbabe;
  {>>{first,second}}=32'h89abcdef;
  #1;$display("TRACE targets %b %h %h",y,first,second);
 end
endmodule
