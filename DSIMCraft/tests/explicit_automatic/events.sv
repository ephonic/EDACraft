`timescale 1ns/1ps
module top;
integer i=0,a=0,b=0,c=0;
task watch(input integer tag);
 automatic integer saved=tag;
 automatic logic local_clock=0;
 automatic logic allow=0;
 fork
  begin #1;local_clock=1;#1;allow=1;end
  begin @(posedge local_clock iff saved>0);a+=saved;end
  begin wait(allow);b+=saved;end
  begin @((local_clock ^ 1'b0));c+=saved;end
 join
endtask
initial begin
 for(i=1;i<=4;i++)fork automatic integer n=i;watch(n);join_none
 wait fork;
 $display("TRACE events %0d %0d %0d",a,b,c);
 if(a!=10||b!=10||c!=10)$fatal(1,"explicit automatic event context");
end
endmodule
