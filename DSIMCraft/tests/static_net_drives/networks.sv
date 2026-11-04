`timescale 1ns/1ps
module net_child(input [7:0] a, output logic [7:0] q, inout [3:0] shared);
  always_comb q = a ^ 8'h69;
  assign shared = a[7] ? a[3:0] : 4'bz;
endmodule
module bit_alias(inout [2:0] bus,input [2:0] a);
  assign bus=a;
endmodule
module top;
  reg [63:0] data=0;
  reg [7:0] other=0;
  reg enable=0;
  wire [63:0] single;
  wire [7:0] second, third, multi, partial, delayed, out;
  wire [3:0] shared;
  wire [7:0] initnet=data[7:0];
  wire loopback;
  wire [3:0] hi,lo;
  assign single=data;
  assign second=single[7:0];
  assign third=second ^ other;
  assign multi=enable ? other : 8'bz;
  assign multi=data[7:0];
  assign partial=data[7:0];
  assign partial[3:0]=enable ? other[3:0] : 4'bz;
  assign #2 delayed=single[7:0];
  assign shared=enable ? other[3:0] : 4'bz;
  assign {hi,lo}=data[7:0];
  assign loopback=enable ? (loopback & data[0]) : 1'b0;
  net_child u(third,out,shared);
  bit_alias v(shared[2:0],data[6:4]);
  integer changes=0, rises=0, falls=0, i;
  always @(single) changes=changes+1;
  always @(posedge single) rises=rises+1;
  always @(negedge single) falls=falls+1;
  initial begin
    #4;
    for(i=0;i<12;i++) begin
      case(i)
        0: data=64'hfedcba9876543210;
        1: data=64'hfedcba9876543210;
        2: data=64'hzzzzzzzzzzzzzzzz;
        3: data=64'hxxxxxxxxxxxxxxxx;
        4: data=64'hx0z1_x0z1_12xz_45zx;
        default: data=(64'h8000000000000001 << (i-5)) ^ (i*17);
      endcase
      other=i*37;enable=i[0];
      #0;
      #3;
      if(single!==data || second!==data[7:0] || third!==(data[7:0]^other) || initnet!==data[7:0]) $fatal(1,"single net");
      $display("TRACE nets %0d %h %h %h %h %h %h %h %h %h %b %0d %0d %0d",i,single,third,multi,partial,delayed,out,shared,hi,lo,loopback,changes,rises,falls);
      data<=~data;other<=other+1;
      #3;
    end
    $display("TRACE complete %0d %0d %0d",changes,rises,falls);
    $finish;
  end
endmodule
