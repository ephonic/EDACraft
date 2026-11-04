`timescale 1ns/1ps
module top;
int unsigned r0,r1,r2,r3,seeded,following,discard;
integer i;
initial begin
 for(i=0;i<4;i++)begin
  r0=$urandom;r1=$urandom_range(200,100);if(r1<100||r1>200)$fatal(1,"random range");
  #1;$display("TRACE default %0d %h %h",i,r0,r1);
 end
 discard=$urandom(5678);seeded=$urandom;following=$urandom;
 discard=$urandom(5678);
 if($urandom!==seeded||$urandom!==following)$fatal(1,"explicit reseed");
 $display("TRACE explicit reseed pass");
end
initial begin
 r2=$urandom;#1;r3=$urandom;
 #1;$display("TRACE second %h %h",r2,r3);
end
endmodule
