`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 reg[7:0]a[0:2];int fd,n,c,r;string text;
 initial begin
  fd=$fopen("memory.txt","w+");$fdisplay(fd,"01 2a ff");$fflush(fd);
  $readmemh("memory.txt",a);$display("TRACE MEM %h %h %h",a[0],a[1],a[2]);
  $fclose(fd);$writememh("export.txt",a);
  fd=$fopen("memory.txt","r");c=$fgetc(fd);$display("TRACE EXPORT %0d",c);$fclose(fd);
  #1;$finish;
 end
endmodule
