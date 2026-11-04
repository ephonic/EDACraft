`timescale 1ns/1ps
module top;
integer k=0,done=0,r1=0,r2=0,r3=0,r4=0;
task automatic launch(input integer n);
 integer shared=n;
 fork
  begin #1;shared++;end
  begin
   #2;
   case(n)
    1:r1=shared;
    2:r2=shared;
    3:r3=shared;
    4:r4=shared;
   endcase
   done++;
  end
 join_none
 shared+=100;
endtask
initial begin
 for(k=1;k<=4;k++)launch(k);
 wait fork;
 $display("TRACE sharing %0d %0d %0d %0d %0d",done,r1,r2,r3,r4);
 if(done!=4||r1!=102||r2!=103||r3!=104||r4!=105)$fatal(1,"parent sharing");
 $finish;
end
endmodule
