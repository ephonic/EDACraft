module top;
  int q[$], result[$], stage=0, calls=0, first;
  function automatic int lower(); calls++; return 1; endfunction
  initial begin
    q='{10,20,30,40,50};
    first=lower(); result=q[first:3]; stage++; #1;
    $display("TRACE calls %0d size=%0d values=%0d/%0d/%0d",calls,result.size(),result[0],result[1],result[2]);
    $display("TRACE methods %0d %0d",result.size(),result.sum());
    $display("TRACE query %0d %0d",$size(q[1:3]),$size(q[0:-1]));
    result=result.find with (item>=30); stage++; #1;
    $display("TRACE find %0d %0d %0d",result.size(),result[0],result[1]);
    $display("TRACE compare %0d",q[2:3]===result);
    $finish;
  end
endmodule
