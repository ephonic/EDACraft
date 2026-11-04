`timescale 1ps/1ps
module unit_test #(parameter int N=2)(output int total);
 class Counter;
  int value;
  function new(int n);value=n;endfunction
  function int add(int n);value+=n;return value;endfunction
 endclass
 Counter p,q;
 initial begin
  total=0;p=new(N);q=p;
  #2;total=p.add(3);
  #2;q.value+=N;total=p.value;
 end
endmodule
module plain(output int total);
 initial begin total=0;#1;total=11;#2;total=23;end
endmodule
module top;
 int one,two,three;
 unit_test #(2) a(one);unit_test #(4) b(two);plain c(three);
endmodule
