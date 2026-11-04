`timescale 1ns/1ps
module top;
logic[2:0] a=0,b=0;integer sa=0,sb=0,ea=0,eb=0;
initial begin
 repeat(4)begin #2;a++;unique case(a) 1:sa+=1;2:sa+=2;3:sa+=3;4:sa+=4;endcase end
 if(sa!==10)ea=1;
end
initial begin repeat(4)begin #3;b++;sb+=b;end if(sb!==10)eb=1;end
endmodule
