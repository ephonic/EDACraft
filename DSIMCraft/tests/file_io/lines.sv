module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 int fd,n,c,r;reg[23:0]p;string s;
 initial begin
 fd=$fopen("lines.txt","w");$fwrite(fd,"abcdefgh\nZ\n");$fclose(fd);
 fd=$fopen("lines.txt","r");
 repeat(5)begin n=$fgets(p,fd);$display("TRACE P %0d %h %0d %0d",n,p,$ftell(fd),$feof(fd));end
 r=$rewind(fd);r=$ungetc(81,fd);$display("TRACE BEFORE %0d %0d",r,$ftell(fd));
 c=$fgetc(fd);$display("TRACE FIRST %0d %0d",c,$ftell(fd));
 r=$ungetc(65,fd);n=$ungetc(66,fd);$display("TRACE DOUBLE %0d %0d %0d",r,n,$ftell(fd));
 repeat(3)begin c=$fgetc(fd);$display("TRACE C %0d %0d",c,$ftell(fd));end
 $fclose(fd);fd=$fopen("lines.txt","a+");$display("TRACE APPOS %0d",$ftell(fd));
 n=$fgets(s,fd);$display("TRACE APREAD %0d %0d %0d %0d",n,s.len(),s.getc(0),s.getc(8));r=$fseek(fd,0,0);$fwrite(fd,"END");$display("TRACE APWRITE %0d",$ftell(fd));
 $fclose(fd);#1;$finish;
 end
endmodule
