`timescale 1ns/1ps
module worker(output integer result);
integer a[],b[];
task automatic grow(inout integer x[]);#2;x=new[x.size()+1](x);x[x.size()-1]=10;endtask
function automatic integer fold(input integer x[]);integer s=0;foreach(x[i])s+=x[i];return s;endfunction
initial begin a=new[2];a[0]=2;a[1]=3;grow(a);b=a;#2;result=fold(b);end
endmodule
module top;
wire signed [31:0] one,two;
worker u(one),v(two);
endmodule
