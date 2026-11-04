`timescale 1ps/1ps
module top;
 mailbox #(int) box=new;
 int one,two;
 initial begin box.get(one);box.get(one);end
 initial begin #2;box.put(7);#2;box.put(9);end
 initial begin #1;two=11;#2;two=23;end
endmodule
