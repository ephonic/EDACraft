`timescale 1ns/1ps
module top;
logic[3:0] x=0;integer q=0;
initial begin
 #1;unique if(x==0)q=1;else if(x<2)q=2;else q=3; // report overlap 1000
 if(q!==1)$fatal(1,"unique first branch");
 #1;x=3;
 unique if(x==0)q=4;else if(x==1)q=5; // report no-match 2000
 unique0 if(x==0)q=4;else if(x==1)q=5;
 priority if(x==0)q=4;else if(x==1)q=5; // report no-match 2000
 if(q!==1)$fatal(1,"no match retains value");
 #1;priority if(x<4)q=6;else if(x==3)q=7;
 if(q!==6)$fatal(1,"priority first branch");
 #1;unique0 if(x<4)q=8;else if(x==3)q=9; // report overlap 4000
 if(q!==8)$fatal(1,"unique0 first branch");
 #1;x=4'bx001;unique if(x==0)q=10;else q=11;
 if(q!==11)$fatal(1,"unknown does not match");
 #1;unique if(x===4'bx001)begin
  priority if(q==11)q=12;else q=13;
 end else q=14;
 #1;$display("TRACE branches %0d",q);
end
endmodule
