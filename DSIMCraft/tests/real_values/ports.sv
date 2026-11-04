`timescale 1ps/1ps
module lane(input real a,output real b);
  always_comb b=a*2.0;
endmodule
module top;
  real a,b,c,d;
  lane one(a,b);lane two(c,d);
  initial begin a=0.5;#2;a=1.25;#2;if(b!=2.5)$fatal(1,"real port one");$display("TRACE one=%0.2f",b);end
  initial begin c=-1.5;#1;c=0.25;#2;if(d!=0.5)$fatal(1,"real port two");$display("TRACE two=%0.2f",d);end
  initial begin #5;$finish;end
endmodule
