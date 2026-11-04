`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
integer fd,r;reg[15:0]a[2:5];
task automatic load(ref reg[15:0] dest[2:5],input integer handle);
 integer n;reg[79:0]local_word;
 begin
 n=$fread(dest,handle,3,2);$display("TRACE array-ref %0d %h %h",n,dest[3],dest[4]);
 r=$rewind(handle);n=$fread(local_word,handle);$display("TRACE local %0d %h",n,local_word);
 end
endtask
initial begin
 fd=$fopen("input.bin","rb");a[2]=16'hfeed;a[5]=16'hfeed;
 #1;load(a,fd);$display("TRACE caller %h %h %h %h",a[2],a[3],a[4],a[5]);
 $fclose(fd);#1;$finish;
end endmodule
