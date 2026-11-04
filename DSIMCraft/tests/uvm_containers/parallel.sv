`timescale 1ns/1ps
module bucket #(parameter int N=2)(output int total);
 int q[$:N], a[int], i;
 initial begin
  total=0;
  for(i=0;i<N;i++)begin q.push_back(i+1);a[-i]=i+2;#1;end
  foreach(q[j])total+=q[j];
  foreach(a[k])total+=a[k];
 end
endmodule
module top;
 int one,two;
 bucket #(2) a(one);bucket #(4) b(two);
endmodule
