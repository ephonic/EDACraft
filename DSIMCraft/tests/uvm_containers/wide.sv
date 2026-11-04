`timescale 1ns/1ps
module top;
 logic signed [95:0] q[$], a[int], copy[$];
 bit [95:0] clean[$];
 logic [95:0] result;
 initial begin
  q.push_back(-1);q.push_front(96'h123456789abc000000000001);q.insert(1,96'hx);
  clean.push_back(96'hx);a[-3]=q[0];a[8]=96'hz;
  copy=q;q.delete(1);result=q.pop_back();
  $display("TRACE wide %h %h %h %h %h",copy[0],copy[1],result,clean[0],a[8]);
  q.delete();q.push_back(32'hffffffff+32'd1);q.insert(64'h100000001,32'hffffffff+32'd2);
  $display("TRACE context %h %h",q[0],q[1]);
  #2;q.delete();result=q.pop_back();
  $display("TRACE default %h %h %h %0d",result,a[-3],a[99],q.size());
 end
endmodule
