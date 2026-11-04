module top;
 int small_q[$:2],large_q[$:4];int stage=0;
 function automatic void widen(ref int data[$]);
  data.push_back(3);data.push_back(4);data[data.size()]=5;
  $display("TRACE append %0d %0d",data.size(),data[$]);
  data='{8,7,6,5,4,3};
  $display("TRACE replace %0d %0d",data.size(),data[$]);
 endfunction
 initial begin
  small_q='{1,2};large_q='{1,2};widen(small_q);widen(large_q);stage++;#1;
  $display("TRACE actual %0d %0d",small_q.size(),large_q.size());$finish;
 end
endmodule
