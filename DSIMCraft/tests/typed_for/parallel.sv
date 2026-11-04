`timescale 1ps/1ps
module top;
 class Cursor;int value;function new(int n);value=n;endfunction endclass
 typedef int count_t;
 int one,two;
 initial for(Cursor cursor=new(1);cursor.value<=3;cursor.value++)begin #1;one+=cursor.value;end
 initial for(count_t index=1;index<=4;index++)begin #1;two+=index;end
endmodule
