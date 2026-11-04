`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
integer fd,n,r;reg[23:0]p;reg[11:0]q;reg[4:0]tiny;reg[79:0]wide;bit[15:0]two;
initial begin
 fd=$fopen("input.bin","rb");p='1;#1;n=$fread(p,fd);$display("TRACE packed %0d %h %0d %0d",n,p,$ftell(fd),$feof(fd));
 r=$fseek(fd,8,0);p='1;#1;n=$fread(p,fd);$display("TRACE short %0d %h %0d %0d",n,p,$ftell(fd),$feof(fd));
 p='1;#1;n=$fread(p,fd);$display("TRACE empty %0d %h",n,p);
 r=$rewind(fd);#1;n=$fread(q,fd);$display("TRACE twelve %0d %h",n,q);
 r=$rewind(fd);#1;n=$fread(tiny,fd);$display("TRACE five %0d %h",n,tiny);
 r=$rewind(fd);#1;n=$fread(wide,fd);$display("TRACE wide %0d %h %0d",n,wide,$feof(fd));
 r=$rewind(fd);r=$ungetc(0,fd);#1;n=$fread(two,fd);$display("TRACE zero %0d %h %0d",n,two,$ftell(fd));
 $fclose(fd);#1;$finish;
end endmodule
