module top;
  timeunit 1ns; timeprecision 1ns;
  bit clk=0;
  logic [7:0] data=0;
  always #5 clk=~clk;
  clocking cb @(posedge clk);
    input #0 sampled=data;
    output #10 driven=data;
  endclocking
  initial begin
    @(cb);cb.driven<=42;
    @(cb);
    if(cb.sampled!==0 || data!==0) $fatal(1,"delayed drive must follow Observed");
    #1;
    if(data!==42) $fatal(1,"delayed Re-NBA delivery");
    @(cb);
    if(cb.sampled!==42) $fatal(1,"next input sample");
    $display("TRACE clocking delayed regions pass");
    $finish;
  end
endmodule
