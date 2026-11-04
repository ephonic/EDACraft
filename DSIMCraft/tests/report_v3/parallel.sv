`timescale 1ns/1ps
module storage;
 typedef enum logic[1:0]{A,B,C} state_t;
 state_t state=B;reg[7:0] mem[0:1];
 initial begin mem[0]=7;mem[1]=9;#1;mem[1]=12;state=C;end
endmodule
module lane(output integer result);
 storage u();integer index=0;
 initial begin #0.5;result=u.mem[index];index=1;#1;result=u.state.name=="C"?result+u.mem[index]:0;end
endmodule
module top;
 wire[31:0] one,two;lane a(one);lane b(two);
 initial begin #2;$finish;end
endmodule
