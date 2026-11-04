`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 int fd,n,done=0,a,b;string first,second;
 function automatic int parse(input string source,ref int target);
  return $sscanf(source,"%d",target);
 endfunction
 task automatic get(input int descriptor,input int delay_ticks,output string answer,ref int count);
  int value,r;string name;r=$fscanf(descriptor,"%d %s",value,name);#delay_ticks;
  answer=$sformatf("%0d:%0d:%s",r,value,name);count++;
 endtask
 initial begin fd=$fopen("auto.txt","w+");$fwrite(fd,"12 one\n34 two\n");n=$rewind(fd);end
 initial begin #1;get(fd,2,first,done);end
 initial begin #2;get(fd,2,second,done);end
 initial begin #5;n=parse("-99",a);b=parse("21",b);$display("TRACE AUTO %0d <%s> <%s> %0d %0d %0d",done,first,second,n,a,b);$fclose(fd);$finish;end
 final begin : final_scan int q,x;q=$sscanf("73","%d",x);$display("TRACE FINAL %0d %0d",q,x);end
endmodule
