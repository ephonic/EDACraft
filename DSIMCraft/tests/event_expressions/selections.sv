`timescale 1ns/1ps
module top;
 logic[7:0] bus,memory[0:1];integer index,bits,dynamic_bits,words,parts;
 wire[15:0] observed={memory[1],memory[0]};
 initial begin bus=0;index=0;memory[0]=3;memory[1]=3;bits=0;dynamic_bits=0;words=0;parts=0;end
 initial begin #0;forever begin @(bus[3]);bits++;end end
 initial begin #0;forever begin @(bus[index]);dynamic_bits++;end end
 initial begin #0;forever begin @(memory[index]);words++;end end
 initial begin #0;forever begin @(bus[5:2]);parts++;end end
 initial begin #1;bus[7]=1;#1;bus[3]=1;memory[1]=9;#1;index=1;
 #1;bus[1]=1;memory[1]=10;#1;index=3;#1;index=0;#1;bus[3]=0;#1;
 if(bits!==2||dynamic_bits!==2||words!==4||parts!==2)$fatal(1,"selected event values");
 $display("TRACE selections %0d %0d %0d %0d",bits,dynamic_bits,words,parts);$finish;end
endmodule
