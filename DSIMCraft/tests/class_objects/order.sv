`timescale 1ps/1ps
module top;
int counter;
class Item;
 int snapshot=counter;
 int value;
 function new(int n);value=n;endfunction
endclass
Item p,q;int observed;
function automatic int next_value();counter++;return counter;endfunction
initial begin
 counter=10;
 p=new(next_value());
 q=new(next_value());
 $display("TRACE order p=%0d/%0d q=%0d/%0d counter=%0d",p.snapshot,p.value,q.snapshot,q.value,counter);
 $finish;
end
endmodule
