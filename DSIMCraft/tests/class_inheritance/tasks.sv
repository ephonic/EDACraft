`timescale 1ps/1ps
module top;
class Worker;
 int value;
 virtual task run(input int n=2,output int result);#1;value=n;result=value;endtask
endclass
class Slow extends Worker;
 task run(input int n=8,output int result);#2;value=n+10;result=value;endtask
endclass
class Slower extends Slow;
 task run(input int n=9,output int result);super.run(n,result);#1;value++;result=value;endtask
endclass
Worker a,b;Slow s;Slower t;int x,y,receivers,arguments;int observed;
function automatic Worker choose();receivers++;return a;endfunction
function automatic int argument();arguments++;return 5;endfunction
initial begin
 s=new;t=new;a=s;b=t;
 fork
  choose().run(argument(),x);
  b.run(.result(y));
 join
 observed=a.value+b.value;
 $display("TRACE tasks t=%0t x=%0d y=%0d total=%0d calls=%0d/%0d",$time,x,y,observed,receivers,arguments);
 $finish;
end
endmodule
