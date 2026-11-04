`timescale 1ps/1ps
module unit_test(output int total);
 typedef class Counter;
 class Counter;
  int value=3;
  function int add(int amount);value+=amount;return value;endfunction
 endclass
 Counter p=new;
 initial begin total=0;#2;total=p.add(4);#2;total=p.add(2);end
endmodule
module plain(output int total);
 initial begin total=0;#1;total=11;#2;total=23;end
endmodule
module top;
 int one,two;
 unit_test a(one);plain b(two);
endmodule
