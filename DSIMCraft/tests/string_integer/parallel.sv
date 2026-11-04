`timescale 1ns/1ps
module lane(output integer result);
  string text;int count=0,errors=0;
  initial begin
    repeat(4) begin
      #0.5;count++;text.hextoa(16'h1000+count);
      if(text.atohex()!=16'h1000+count)errors++;
      text.putc(0,8'h32);
      if(text.atohex()!=16'h2000+count)errors++;
      result=text.atohex();
    end
  end
endmodule
module top;
  wire[31:0] first,second;
  lane u(first);lane v(second);
  initial begin #3;$finish;end
endmodule
