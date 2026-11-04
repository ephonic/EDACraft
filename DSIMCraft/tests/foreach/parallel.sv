`timescale 1ns/1ps
module top;
  logic[4:0] a=0,b=0;
  integer sa=0,sb=0,ea=0,eb=0;
  initial foreach(a[i])begin #2;a[i]=1;sa+=i;if(sa!=(4+i)*(5-i)/2)ea++;end
  initial foreach(b[j])begin #3;b[j]=1;sb+=j;if(sb!=(4+j)*(5-j)/2)eb++;end
endmodule
