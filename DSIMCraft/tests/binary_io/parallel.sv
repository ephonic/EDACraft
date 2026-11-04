`timescale 1ns/1ps
module compute(output integer value);
 int count=0;initial repeat(8)begin #0.25;count++;value=count*7;end
endmodule
module io_lane(output integer total);
 int fd,n;reg[15:0]word;
 initial begin
 fd=$fopen("input.bin","rb");total=0;
 repeat(4)begin #0.5;n=$fread(word,fd);total+=word;end
 #0.5;$fclose(fd);$display("TRACE parallel %0d",total);
 end
endmodule
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 wire[31:0]answer,total;compute u(answer);io_lane v(total);
 initial begin #3;$finish;end
endmodule
