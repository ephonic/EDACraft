`timescale 1ns/1ps
module lane #(parameter BASE=3)(output reg [31:0] q=0);
function integer calc(input integer n);
 integer total;
 begin
  total=BASE;
  for(int i=0;i<6;i+=1)begin
   if(i==n)return total;
   total+=3;
  end
  return -1;
 end
endfunction
task step(input integer n,output integer result);
 begin #1;result=calc(n);return;result=999;end
endtask
initial begin : run
 integer temp;
 for(int i=0;i<5;i+=1)begin
  step(i,temp);q<=#1 temp;
 end
end
endmodule
module top;
wire [31:0] a,b;
lane #(3) u(a);lane #(17) v(b);
endmodule
