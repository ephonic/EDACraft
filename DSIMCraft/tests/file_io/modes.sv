`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 string filename="modes.bin",mode="wb+";int fd,a,b,c,n,r;reg[127:0]bytes;
 initial begin
  fd=$fopen(filename,mode);$fwrite(fd,"%c%c%c%c",0,255,65,10);r=$rewind(fd);
  a=$fgetc(fd);b=$fgetc(fd);n=$fgets(bytes,fd);c=$fgetc(fd);
  $display("TRACE BYTES %0d %0d %0d %h %0d %0d",a,b,n,bytes,c,$feof(fd));
  r=$ungetc(-1,fd);$display("TRACE NOUNGET %0d %0d",r,$feof(fd));$fclose(fd);
  fd=$fopen(filename,"r+b");r=$fseek(fd,1,0);$fwrite(fd,"Z");$fflush();$fclose(fd);
  fd=$fopen(filename,"ab");$display("TRACE APPEND %0d",$ftell(fd));r=$fseek(fd,0,0);$fwrite(fd,"END");$fclose(fd);
  fd=$fopen(filename,"rb");n=$fgets(bytes,fd);$display("TRACE READ %0d %h",n,bytes);
  r=$fseek(fd,2,1);c=$fgetc(fd);$display("TRACE REL %0d %0d %0d",r,c,$ftell(fd));$fclose(fd);
  fd=$fopen("missing-parent/out.txt","w");$display("TRACE BADPATH %0d",fd);
  #1;$finish;
 end
endmodule
