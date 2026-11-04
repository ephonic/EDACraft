`timescale 1ps/1ps
module top;
 class Cursor;int value;function new(int n);value=n;endfunction endclass
 typedef int count_t;
 int observed;
 initial begin
  for(Cursor cursor=new(1);cursor.value<5;cursor.value++)begin
   #1;
   for(count_t j=0;j<cursor.value;j++)observed+=cursor.value;
  end
  if(observed!=30)$fatal(1,"loop replay state");
  $display("TRACE rollback %0d",observed);#1;$finish;
 end
endmodule
