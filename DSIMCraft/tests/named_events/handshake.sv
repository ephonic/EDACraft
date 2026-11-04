`timescale 1ns/1ps
module top;
 event request,reply;logic done;logic[7:0]data;integer sent,received,sum;
 task automatic send(input integer value);
   begin #1;data=value;->>request;@reply;sent++;end
 endtask
 initial begin done=0;data=0;sent=0;send(7);send(11);send(19);done=1;end
 initial begin received=0;sum=0;repeat(3)begin @request;sum+=data;received++;#1;->reply;end end
 initial begin wait(done);#1;
   if(sent!==3||received!==3||sum!==37)$fatal(1,"event handshake");
   $display("TRACE handshake %0d %0d %0d",sent,received,sum);$finish;
 end
endmodule
