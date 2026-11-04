`timescale 1ns/1ps
module top;
logic [7:0] a,q,before_word,after_word;
logic flag;
logic [129:0] wide,wide_read;
logic [1:0][3:0] packed_q;
always_comb begin
  before_word=q; // This read must not cause implicit self-triggering.
  q=a;q[7]=flag;q[3:2]=2'bxz;after_word=q;
  wide={2'bxz,{16{a}}};wide[65+:4]=q[3:0];wide_read=wide;
  {packed_q}=a;packed_q[1][0]=flag;
end
initial begin
 #1; a=8'h12;flag=0;
 #1;$display("TRACE static %b %b %b %b %b %b",q,before_word,after_word,wide,wide_read,packed_q);
 a=8'hf3;flag=1;
 #1;$display("TRACE static %b %b %b %b %b %b",q,before_word,after_word,wide,wide_read,packed_q);
 a=8'bxz101010;flag=1'bz;
 #1;$display("TRACE static %b %b %b %b %b %b",q,before_word,after_word,wide,wide_read,packed_q);$finish;
end
endmodule
