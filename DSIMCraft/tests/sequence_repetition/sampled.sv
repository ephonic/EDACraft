`timescale 1ns/1ps
module top;
  reg clk=0,req=1,data=0,rst=0;
  integer tick=0,passed=0,failed=0,covered=0,changed_pass=0,changed_fail=0;
  always #5 clk=~clk;
  ap:assert property(@(posedge clk) disable iff(rst) req |-> ($past(data)===data)[*3] ##0 $stable(data)) passed++;else failed++;
  cp:cover property(@(posedge clk) disable iff(rst) req |=> $sampled(data)[*2] ##1 $past(data)) covered++;
  sp:assert property(@(posedge clk) disable iff(rst) req |-> $changed(data)[*2]) changed_pass++;else changed_fail++;
  initial begin
    repeat(16) begin
      #7;
      $display("TRACE sampled-repeat %0d %0d %0d %0d %0d %0d",tick,passed,failed,covered,changed_pass,changed_fail);
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
