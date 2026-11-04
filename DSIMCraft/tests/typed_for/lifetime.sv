`timescale 1ps/1ps
module top;
 class Cursor;int value;function new(int n);value=n;endfunction endclass
 int class_steps,int_steps,done;
 task run;
  for(Cursor cursor=new(0);cursor.value<3;cursor.value++)begin
   #2;class_steps++;
  end
  for(int index=0;index<3;index++)begin #2;int_steps++;end
  done++;
 endtask
 initial begin
  fork run();begin #1;run();end join
  run();
  if(class_steps!=9 || int_steps!=9 || done!=3)$fatal(1,"automatic loop lifetime %0d %0d %0d",class_steps,int_steps,done);
  $display("TRACE lifetime %0d %0d %0d",class_steps,int_steps,done);
 end
endmodule
