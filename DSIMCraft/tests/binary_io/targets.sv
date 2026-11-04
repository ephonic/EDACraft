`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
integer fd,n,r,k,i;reg[15:0]a[0:3];reg[31:0]p;
function automatic integer get_fd();begin k=2;get_fd=fd;end endfunction
function automatic integer read_word(ref reg[15:0] dest,input integer handle);read_word=$fread(dest,handle);endfunction
initial begin
 fd=$fopen("input.bin","rb");for(i=0;i<4;i++)a[i]=16'hfeed;k=0;
 #1;n=$fread(a[k++],get_fd());$display("TRACE order %0d %0d %h %h",n,k,a[0],a[2]);
 r=$fseek(fd,8,0);k=0;#1;n=$fread(a[k++],fd);$display("TRACE selected-short %0d %0d %h",n,k,a[0]);
 k=0;#1;n=$fread(a[k++],fd);$display("TRACE selected-empty %0d %0d %h",n,k,a[0]);
 r=$fseek(fd,8,0);p=32'habcdef01;#1;n=$fread(p[23:8],fd);$display("TRACE part %0d %h",n,p);
 p=32'habcdef01;#1;n=$fread(p[23:8],fd);$display("TRACE part-empty %0d %h",n,p);
 r=$rewind(fd);#1;n=read_word(a[1],fd);$display("TRACE ref %0d %h",n,a[1]);
 $fclose(fd);#1;$finish;
end endmodule
