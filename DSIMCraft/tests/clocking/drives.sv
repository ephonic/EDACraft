module top;
  timeunit 1ns; timeprecision 1ns;
  bit clk=0;
  logic [7:0] immediate=0, later=0, value=7;
  always #5 clk=~clk;
  clocking cb @(posedge clk);
    input #0 observed=immediate;
    output #0 zero=immediate;
    output #2 delayed=later;
  endclocking
  initial begin
    @(cb);
    cb.zero<=3;
    cb.delayed<=value;
    value=99;
    if(immediate!==0 || cb.observed!==0) $fatal(1,"drive must await Re-NBA");
    #1;
    if(immediate!==3 || later!==0) $fatal(1,"output zero skew");
    #2;
    if(later!==7 || cb.observed!==0) $fatal(1,"output snapshot and retained input");
    cb.zero<=9;
    #6;
    if(immediate!==3) $fatal(1,"off-clock drive must await next event");
    @(cb);
    if(cb.observed!==3) $fatal(1,"sample precedes output drive");
    #1;
    if(immediate!==9) $fatal(1,"pending output drive");
    $display("TRACE clocking drives %0d %0d",immediate,later);
    $finish;
  end
endmodule
