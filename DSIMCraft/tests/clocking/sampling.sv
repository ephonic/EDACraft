module top;
  timeunit 1ns; timeprecision 1ns;
  bit clk=0;
  logic [7:0] data=0;
  always #5 clk=~clk;
  always @(posedge clk) data<=data+1;
  clocking prior @(posedge clk);
    input #1step old_data=data;
  endclocking : prior
  clocking current @(posedge clk);
    input #0 new_data=data;
  endclocking
  initial begin
    for(int i=0;i<3;i++) begin
      @(prior);
      if(prior.old_data!==i || current.new_data!==i+1 || data!==i+1)
        $fatal(1,"clocking sample regions");
      $display("TRACE samples %0d %0d %0d",i,prior.old_data,current.new_data);
    end
    $finish;
  end
endmodule
