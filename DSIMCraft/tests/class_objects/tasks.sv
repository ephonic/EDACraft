`timescale 1ps/1ps
module top;
class Worker;
 int value;
 function new(int n);value=n;endfunction
 task advance(int n,int ticks);#(ticks);value+=n;endtask
endclass
Worker a,b;int observed_a,observed_b;
initial begin
 a=new(1);b=new(10);
 fork
  a.advance(3,2);
  b.advance(5,4);
 join
 observed_a=a.value;observed_b=b.value;
 $display("TRACE tasks=%0t a=%0d b=%0d",$time,a.value,b.value);
 $finish;
end
endmodule
