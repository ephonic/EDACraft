`timescale 1ns/1ps
module top;
 logic [15:0] a[];
 logic [15:0] q=0,r=0;
 integer i=0,k=0,calls=0;
 event e;
 task automatic local_edit(input integer n,output logic[15:0] result);
  logic[15:0] x[];
  x=new[1];x[0]=16'h1200;
  x[0][3:0]=n;
  #1;x[0][7:4]=n+1;
  result=x[0];
 endtask
 initial begin
  a=new[2];a[0]=16'h1234;a[1]=16'habcd;
  fork
   begin a[i][k+:4]=#2 4'h9;end
   begin #1;i=1;k=12;end
  join
  q=a[0];r=a[1];
  $display("TRACE delay %h %h",q,r);
  fork
   begin a[i][k-:4]=@(e) 4'h5;end
   begin #1;i=0;k=7;->e;end
  join
  q=a[0];r=a[1];
  $display("TRACE event %h %h",q,r);
  for(calls=1;calls<=4;calls++)local_edit(calls,q);
  $display("TRACE local %h %0d",q,calls);
  #1;$finish;
 end
endmodule
