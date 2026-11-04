module top;
  bit clk=0;
  int observed=0;
  always #5 clk=~clk;
  clocking cb @(posedge clk); endclocking
  initial begin
    fork
      begin @(cb);observed=99;end
      begin #2;end
    join_any
    disable fork;
    #4;
    if(observed!==0) $fatal(1,"cancelled clocking waiter resumed");
    fork
      begin @(cb);observed=2;end
      begin #12;end
    join_any
    disable fork;
    if(observed!==2) $fatal(1,"clocking wait after fork slot reuse");
    $display("TRACE clocking cancellation %0d",observed);
    $finish;
  end
endmodule
