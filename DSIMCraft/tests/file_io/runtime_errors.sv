module top;
 int kind,fd,n;string text;
 initial begin
  n=$value$plusargs("error=%d",kind);
  case(kind)
   1:fd=$fopen("bad.txt","bogus");
   2:begin fd=$fopen("closed.txt","w");$fclose(fd);n=$fgetc(fd);end
   3:begin fd=$fopen("readonly.txt","w");$fclose(fd);fd=$fopen("readonly.txt","r");$fwrite(fd,"bad");end
   4:n=$fseek(32'hxxxx,0,0);
   5:begin fd=$fopen("format.txt","w");$fwrite(fd,"%p",1);end
  endcase
 end
endmodule
