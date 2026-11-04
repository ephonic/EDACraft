`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 int first,second,fd,n;string path="channel";reg[159:0]line;
 initial begin
  first=$fopen({path,"1.txt"});second=$fopen({path,"2.txt"});
  $fdisplay(first|second|1,"TRACE CHANNEL %0h %0d",128'habcdef0123456789abcdef0123456789,-7);
  $fwrite(first,"tail");$fflush(first|second);$fclose(first|second);
  fd=$fopen({path,"1.txt"},"r");n=$fseek(fd,-4,2);n=$fgets(line,fd);
  $display("TRACE TAIL %0d %h %0d",n,line,$feof(fd));$fclose(fd);
  #1;$finish;
 end
endmodule
