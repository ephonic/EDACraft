`timescale 1ns/1ps
module top;
  reg clk=0,req=1,b=1,c=0;
  integer tick=0,passed=0,failed=0,covered=0,late_pass=0,late_fail=0,direct_pass=0,direct_fail=0,once_pass=0,once_fail=0;
  always #5 clk=~clk;
  ap:assert property(@(posedge clk) req |-> b[*3] ##1 c) passed++;else failed++;
  cp:cover property(@(posedge clk) req |-> b[*3] ##1 c) covered++;
  np:assume property(@(posedge clk) req |=> ##1 b[*2] ##0 c[*2]) late_pass++;else late_fail++;
  dp:assert property(@(posedge clk) b[*2] ##0 c[*1]) direct_pass++;else direct_fail++;
  op:assert property(@(posedge clk) req |-> b[*1]) once_pass++;else once_fail++;
  initial begin
    repeat(16) begin
      #7;
      $display("TRACE repeat %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",tick,passed,failed,covered,late_pass,late_fail,direct_pass,direct_fail,once_pass,once_fail);
      #3;tick++;
      req=(tick%4!=1);c=(tick%3!=0);
      case(tick%7)
        2:b=1'bx;
        3:b=1'bz;
        5:b=0;
        default:b=1;
      endcase
    end
    #1;$finish;
  end
endmodule
