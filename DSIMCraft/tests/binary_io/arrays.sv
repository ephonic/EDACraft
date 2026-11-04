`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
integer fd,n,r,i;reg[15:0]a[2:5],b[5:2];reg[11:0]q[1:3];
task reset_arrays;begin for(i=2;i<=5;i++)begin a[i]=16'hfeed;b[i]=16'hfeed;end end endtask
initial begin
 fd=$fopen("input.bin","rb");reset_arrays();#1;n=$fread(a,fd);$display("TRACE asc %0d %h %h %h %h %0d",n,a[2],a[3],a[4],a[5],$ftell(fd));
 r=$rewind(fd);#1;n=$fread(b,fd);$display("TRACE desc %0d %h %h %h %h",n,b[5],b[4],b[3],b[2]);
 r=$rewind(fd);reset_arrays();#1;n=$fread(a,fd,3,2);$display("TRACE range %0d %h %h %h %h",n,a[2],a[3],a[4],a[5]);
 r=$rewind(fd);reset_arrays();#1;n=$fread(b,fd,3,2);$display("TRACE descending-range %0d %h %h %h %h",n,b[5],b[4],b[3],b[2]);
 r=$fseek(fd,8,0);reset_arrays();#1;n=$fread(a,fd);$display("TRACE short-array %0d %h %h %0d %0d",n,a[2],a[3],$ftell(fd),$feof(fd));
 r=$rewind(fd);#1;n=$fread(a,fd,3,0);$display("TRACE count-zero %0d %0d",n,$ftell(fd));
 #1;n=$fread(a,fd,4,10);$display("TRACE clamp %0d %h %h %0d",n,a[4],a[5],$ftell(fd));
 r=$rewind(fd);#1;n=$fread(q,fd);$display("TRACE twelve-array %0d %h %h %h",n,q[1],q[2],q[3]);
 $fclose(fd);#1;$finish;
end endmodule
