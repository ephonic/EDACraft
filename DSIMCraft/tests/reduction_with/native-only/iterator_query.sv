module top;
 logic[15:8] a[2]='{8'h12,8'h34};integer l,r,w,lo,hi;
 initial begin
 l=a.sum with($left(item));r=a.sum with($right(item));w=a.sum with($bits(item));
 lo=a.sum with(int'(item[3:0]));hi=a.sum with(int'(item[11:8]));
 $display("TRACE iterator %0d %0d %0d %0d %0d",l,r,w,lo,hi);
 end
endmodule
