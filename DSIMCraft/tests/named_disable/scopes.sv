`timescale 1ns/1ps
module top;integer a=0,b=0,c=0;
task automatic work(input integer n,output integer value);
 integer hold=n;
 value=hold;
 begin : active
  fork : race
   begin #n;value=value+10;disable active;value=77;end
   begin #20;value=99;end
  join : race
  value=88;
 end : active
 value=value+1;
endtask
initial begin
 fork work(1,a);work(3,b);begin #5;work(2,c);end join
 #25;$display("TRACE scopes %0d %0d %0d %0t",a,b,c,$time);
 if(a!==12||b!==4||c!==13)$fatal(1,"automatic cancel mismatch");
 $finish;
end
endmodule
