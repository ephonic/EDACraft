`timescale 1ns/1ps
module top;
  reg clk=0,req=1,data=0,rst=0;
  integer tick=0,passed=0,failed=0,covered=0,changed_pass=0,changed_fail=0;
  always #5 clk=~clk;
  ap:assert property(@(posedge clk) disable iff(rst) req ##1 history |-> history[*2]) passed++;else failed++;
  cp:cover property(@(posedge clk) disable iff(rst) (req ##0 change)[*2] |=> snapshot()[*2]) covered++;
  sp:assert property(@(posedge clk) disable iff(rst) ($rose(req) ##1 change) |-> $past(data) ##0 $sampled(data)) changed_pass++;else changed_fail++;
  sequence history; ($past(data)===data) ##0 $stable(data);endsequence
  sequence snapshot(); $sampled(data) ##1 $past(data);endsequence
  sequence change; ($changed(data)[*1]) ##0 (data===data);endsequence
  initial begin
    repeat(16) begin
      #7;
      $display("TRACE sampled-antecedent %0d %0d %0d %0d %0d %0d",tick,passed,failed,covered,changed_pass,changed_fail);
      // An asynchronous reset pulse entirely between sample clocks must
      // cancel every in-flight repeated match, including overlapping ones.
      if(tick==2||tick==9)begin rst=1;#1;rst=0;#2;end
      else #3;
      tick++;req=(tick%5!=3);
      case(tick%8)
        1,2,3:data=1;
        4:data=1'bx;
        5:data=1'bz;
        default:data=0;
      endcase
    end
    #1;$finish;
  end
endmodule
