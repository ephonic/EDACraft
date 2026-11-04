`timescale 1ns/1ps
module top;
 logic req,ack,done;logic[7:0]data;integer sent,received,sum;
 task automatic send(input integer value);
   begin #1;data=value;req=1;wait(ack);req=0;wait(!ack);sent=sent+1;end
 endtask
 initial begin req=0;done=0;data=0;sent=0;
   send(7);send(11);send(19);done=1;
 end
 initial begin ack=0;received=0;sum=0;
   repeat(3)begin wait(req);sum=sum+data;received=received+1;
     #1;ack<=1;wait(!req);#1;ack<=0;
   end
 end
 initial begin wait(done);#1;
   if(sent!==3||received!==3||sum!==37||req!==0||ack!==0)$fatal(1,"handshake");
   $display("TRACE handshake %0d %0d %0d",sent,received,sum);$finish;
 end
endmodule
