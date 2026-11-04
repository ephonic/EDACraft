`timescale 1ns/1ps
module top;
  reg clk=0,req=1,b=1,c=1;
  integer tick=0,passed=0,failed=0,covered=0,late_pass=0,late_fail=0,direct_pass=0,direct_fail=0,once_pass=0,once_fail=0;
  always #5 clk=~clk;
  ap:assert property(@(posedge clk) req |-> response[*3] ##1 response()) passed++;else failed++;
  cp:cover property(@(posedge clk) req |-> response[*3] ##1 response()) covered++;
  np:assume property(@(posedge clk) req |=> ##1 burst ##0 c) late_pass++;else late_fail++;
  dp:assert property(@(posedge clk) next_pair ##0 ((b && c)[*1])) direct_pass++;else direct_fail++;
  op:assert property(@(posedge clk) req |-> (b && c)[*1]) once_pass++;else once_fail++;
  sequence response(); b ##0 c;endsequence:response
  sequence burst; (response()[*2] ##1 b)[*2];endsequence
  sequence next_pair; b ##1 c;endsequence
  initial begin
    repeat(16) begin
      #7;
      $display("TRACE named-seq %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",tick,passed,failed,covered,late_pass,late_fail,direct_pass,direct_fail,once_pass,once_fail);
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
