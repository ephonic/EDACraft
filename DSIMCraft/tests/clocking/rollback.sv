module top;
  timeunit 1ns; timeprecision 1ns;
  bit clk=0;
  logic [7:0] data=0;
  always #2 clk=~clk;
  clocking cb @(posedge clk);
    input #0 sampled=data;
    output #3 driven=data;
  endclocking
  initial begin
    #1;cb.driven<=7;
    @(cb);
    if(cb.sampled!==0) $fatal(1,"initial clocking sample");
    #1;cb.driven<=9;
    @(cb);
    if(cb.sampled!==7) $fatal(1,"saved pending delayed drive");
    @(cb);
    if(cb.sampled!==9) $fatal(1,"saved off-clock pending drive");
    $display("TRACE clocking rollback %0d",cb.sampled);
    $finish;
  end
endmodule
