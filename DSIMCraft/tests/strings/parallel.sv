`timescale 1ns/1ps
module lane(output integer result);
 string text="seed";integer count=0;
 initial begin
  repeat(3)begin #0.5;text={text,"123456789abcdef"};count=count+1;end
  if(text.len()==49&&text.substr(0,3)=="seed")result=text.len();else result=0;
 end
endmodule
module top;
 wire[31:0] one,two;lane a(one);lane b(two);
 initial begin #2;$finish;end
endmodule
