`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 int fd,n,p,e,c,a=100,b=200;reg[31:0]raw;string s;
 initial begin
  fd=$fopen("scan.txt","w+");$fwrite(fd," 12x 34 Q\n56");n=$rewind(fd);
  #1;n=$fscanf(fd,"%d%d",a,b);p=$ftell(fd);e=$feof(fd);
  $display("TRACE F1 %0d %0d %0d %0d %0d",n,a,b,p,e);
  #1;n=$fscanf(fd,"%d",a);p=$ftell(fd);c=$fgetc(fd);$display("TRACE FAIL %0d %0d %0d %0d",n,a,p,c);
  #1;n=$fscanf(fd,"%c %d ",raw,a);p=$ftell(fd);e=$feof(fd);$display("TRACE F2 %0d %h %0d %0d %0d",n,raw,a,p,e);
  #1;n=$fscanf(fd,"%d",a);$display("TRACE EOF %0d %0d %0d %0d",n,a,$ftell(fd),$feof(fd));
  #1;n=$ungetc(65,fd);n=$fscanf(fd,"%c",s);$display("TRACE PUSH %0d <%s> %0d %0d",n,s,$ftell(fd),$feof(fd));
  #1;n=$rewind(fd);n=$fscanf(fd," %*2d%c %2d",raw,a);$display("TRACE SUP %0d %h %0d %0d",n,raw,a,$ftell(fd));
  $fclose(fd);
  #1;fd=$fopen("nul.bin","w+");$fwrite(fd,"%c%c",0,65);n=$rewind(fd);n=$fscanf(fd,"%c%c",raw,a);$display("TRACE NUL %0d %h %0d %0d",n,raw,a,$ftell(fd));
  $fclose(fd);#1;$finish;
 end
endmodule
