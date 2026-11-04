`timescale 1ns/1ps
module compute(output integer value);
 int count=0;
 initial repeat(8)begin #0.25;count++;value=count*7;end
endmodule
module io_lane(output integer total);
 int fd,n;reg[31:0]line;
 int initial_fd=$fopen("parallel.txt","w+");
 initial begin
  fd=initial_fd;$fwrite(fd,"1\n2\n3\n");n=$rewind(fd);total=0;
  repeat(3)begin #0.5;n=$fgets(line,fd);total+=int'(line[15:8])-48;end
  #0.5;$fclose(fd);$display("TRACE PAR %0d",total);
 end
endmodule
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 wire[31:0]answer,total;compute u(answer);io_lane v(total);
 initial begin #3;$finish;end
endmodule
