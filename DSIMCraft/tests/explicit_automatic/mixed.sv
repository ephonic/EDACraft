`timescale 1ns/1ps
module top;
integer a=0,b=0,q=0;
task work(input integer n,output integer result);
 automatic integer saved=n;
 #saved;result=saved+n;q+=saved;
endtask
initial work(2,a);
initial begin #1;work(4,b);end
initial begin
 #6;$display("TRACE task %0d %0d %0d",a,b,q);
 if(a!=6||b!=8||q!=6)$fatal(1,"static formal and automatic local");
end
endmodule
