`timescale 1ns/1ps
module top;
integer i=0,k=0,q=0,done=0,ret=0;
integer escaped_q=0,bad=0,returned=0;
task automatic launch_escape(input integer n);
 begin : escaped
  fork
   begin #1;escaped_q+=n;disable escaped;end
   begin #2;bad++;end
  join_none
 end
 returned++;
endtask
task automatic launch(input integer n,output integer value);
 integer shared=n;
 begin : body
  integer local_value=shared*2;
  fork
   begin #1;shared+=local_value;q+=shared;done++;end
   begin #3;q+=1000;end
  join_any
  disable fork;
  if(n==2)begin value=shared;return;end
  begin : inner
   integer extra=shared+1;
   while(1)begin
    integer temporary=extra+1;
    value=temporary;
    break;
   end
   disable inner;
   value=999;
  end
 end
endtask
initial begin
 for(i=0;i<25;i++)begin
  for(k=1;k<=3;k++)begin launch(k,ret);q+=ret;end
 end
 $display("TRACE control %0d %0d %0d",q,done,ret);
 if(q!=1000||done!=75||ret!=11)$fatal(1,"frame unwind/recycle");
 launch_escape(7);
 #3;
 launch_escape(9);
 wait fork;
 #0;
 $display("TRACE escaped cancel %0d %0d %0d",escaped_q,bad,returned);
 if(escaped_q!=16||bad!=0||returned!=2)$fatal(1,"returned task restarted");
 $finish;
end
endmodule
