module top;
 bit[0:0] v[2];bit s[2];integer vd,sd;
 initial begin
 vd=v.sum with($dimensions(item));sd=s.sum with($dimensions(item));
 $display("TRACE shape %0d %0d",vd,sd);
 end
endmodule
