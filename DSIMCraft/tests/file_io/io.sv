`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 int fd,mc,n,c,r,at;string s="keep";reg[31:0] p;
 initial begin
  fd=$fopen("data.txt","w+");mc=$fopen("multi.txt");
  $display("TRACE OPEN %0d %0d",fd!=0,mc!=0);
  $fwrite(fd,"abc\nlast");$fflush(fd);at=$ftell(fd);$display("TRACE POS %0d",at);
  r=$fseek(fd,0,0);$display("TRACE SEEK %0d %0d",r,$ftell(fd));
  n=$fgets(p,fd);$display("TRACE PACK %0d %h %0d",n,p,$feof(fd));
  n=$fgets(s,fd);$display("TRACE LINE %0d <%s> %0d",n,s,$feof(fd));
  n=$fgets(s,fd);$display("TRACE END %0d <%s> %0d",n,s,$feof(fd));
  r=$rewind(fd);c=$fgetc(fd);$display("TRACE CHAR %0d %0d %0d",r,c,$ftell(fd));
  r=$ungetc(90,fd);$display("TRACE UNGET %0d %0d %0d",r,$ftell(fd),$feof(fd));
  c=$fgetc(fd);$display("TRACE AGAIN %0d %0d",c,$ftell(fd));
  r=$fseek(fd,-2,2);c=$fgetc(fd);$display("TRACE TAIL %0d %0d %0d",r,c,$ftell(fd));
  r=$fseek(fd,-100,0);$display("TRACE BADSEEK %0d %0d",r,$ftell(fd));
  $fdisplay(mc|1,"TRACE MCD %0d",12);$fclose(mc);$fclose(fd);
  fd=$fopen("missing.txt","r");$display("TRACE MISSING %0d",fd);
  #1;$finish;
 end
endmodule
