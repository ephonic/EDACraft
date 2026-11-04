`timescale 1ns/1ps
module top;
integer q=0,done=0,bad=0,i=0;
task automatic step(input integer n);
 begin : body
  static integer calls=0;
  automatic integer saved=n;
  calls++;
  fork
   begin #1;q+=calls+saved;end
   begin #20;bad++;end
  join_any
  disable fork;
  done++;
  if(n==2)disable body;
 end
endtask
initial begin
 for(i=1;i<=12;i++)begin
  step(i);
 end
 $display("TRACE control %0d %0d %0d",q,done,bad);
 if(q!=156||done!=12||bad!=0)$fatal(1,"static block persistence/cancel");
end
endmodule
