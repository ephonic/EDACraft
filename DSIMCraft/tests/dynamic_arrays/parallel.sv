`timescale 1ns/1ps
module worker(output integer result);
integer a[],b[],total=0;
initial begin
 a=new[4];foreach(a[i])a[i]=i+2;
 #2;b=new[6](a);b[4]=10;b[5]=20;
 foreach(b[j])total+=b[j];
 #2;result=total;b.delete();a.delete();
end
endmodule
module top;
wire signed [31:0] one,two;
worker u(one),v(two);
endmodule
