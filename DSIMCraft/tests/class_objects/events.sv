`timescale 1ps/1ps
module top;
class State;int value;endclass
State p,q;int observed;
initial begin
 p=new;q=p;
 fork
  begin @(p.value);observed=p.value;$display("TRACE event=%0t value=%0d",$time,p.value);end
  begin wait(q.value==5);observed=q.value;$display("TRACE wait=%0t value=%0d",$time,q.value);end
  begin #2;q.value=3;#2;p.value=5;end
 join
 p=null;q.value=9;
 $finish;
end
endmodule
