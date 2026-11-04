`timescale 1ns/1ps
module top;
  logic data[1:3];
  integer stamp=0,counts=0,done=0;
  task walk();
    foreach(data[i]) begin:body
      integer calls=0;
      #2;stamp=stamp*10+i;calls++;counts=counts*10+calls;
    end
  endtask
  initial begin walk();done++;end
  initial begin #1;walk();done++;end
  initial begin
    #8;if(stamp!=112233 || counts!=123456 || done!=2)$fatal(1,"static task foreach activation");
    $display("TRACE overlap %0d",stamp);
  end
endmodule
