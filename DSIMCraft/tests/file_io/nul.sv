module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 int fd,n,r,c;string s;reg[63:0]p;
 initial begin
  fd=$fopen("nul.txt","w+");$fwrite(fd,"A%cB\n",0);r=$rewind(fd);
  n=$fgets(p,fd);$display("TRACE NUL PACK %0d %h %0d",n,p,$ftell(fd));r=$rewind(fd);
  n=$fgets(s,fd);$display("TRACE NUL STRING %0d %0d %0d %0d %0d %0d",n,s.len(),s.getc(0),s.getc(1),s.getc(2),$ftell(fd));
  $fclose(fd);#1;$finish;
 end
endmodule
