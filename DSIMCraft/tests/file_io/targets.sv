module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
int fd,n,i=0;reg[31:0]a[0:7];string s="original";
initial begin
 fd=$fopen("target.txt","w+");$fwrite(fd,"A\nB\n");n=$rewind(fd);
 n=$fgets(a[i++],fd);$display("TRACE T1 %0d %0d %h %h",n,i,a[0],a[1]);
 n=$fgets(a[i++],fd);$display("TRACE T2 %0d %0d %h %h %h %h",n,i,a[0],a[1],a[2],a[3]);
 n=$fgets(a[i++],fd);$display("TRACE T3 %0d %0d %h %h",n,i,a[4],a[5]);
 n=$fgets(s,fd);$display("TRACE T4 %0d <%s>",n,s);
 $fclose(fd);#1;$finish;
end endmodule
