module top;
  timeunit 1ns; timeprecision 1ns;
  bit clk=0;
  int count=0;
  always #1 clk=~clk;
  always @(posedge clk) count<=count+1;
  default clocking cb @(posedge clk);
    input #0 count;
  endclocking
  task check_cycles;
    ##2;
    if(cb.count!==5) $fatal(1,"task lexical default clocking");
  endtask
  initial begin
    ##3;
    if(cb.count!==3) $fatal(1,"default clocking cycle delay");
    check_cycles();
    $display("TRACE clocking cycles %0d",cb.count);
    $finish;
  end
endmodule
