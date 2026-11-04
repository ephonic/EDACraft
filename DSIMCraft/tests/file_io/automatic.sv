`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 int fd,done=0,result;string first,second;
 function automatic int next(input int descriptor);return $fgetc(descriptor);endfunction
 task automatic get_line(input int descriptor,input int delay_ticks,output string answer,ref int count);
  string line;int n;n=$fgets(line,descriptor);#delay_ticks;answer=$sformatf("%0d:%s",n,line);count++;
 endtask
 initial begin fd=$fopen("auto.txt","w+");$fwrite(fd,"first\nsecond\nZ");result=$rewind(fd);end
 initial begin #1;get_line(fd,1,first,done);end
 initial begin #2;get_line(fd,2,second,done);end
 initial begin #5;result=next(fd);$display("TRACE AUTO %0d %0d %0d %0d %0d",done,first.len(),second.len(),result,$ftell(fd));$fclose(fd);$finish;end
 final begin : write_final int f;f=$fopen("final.txt","w");$fdisplay(f,"done=%0d char=%0d",done,result);$fclose(f);end
endmodule
