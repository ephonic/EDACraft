`timescale 1ns/1ps
module top;
 event pulse,immediate,clocked;integer ticks,calls,seen,total,stage,observed,batch_count,always_count;
 logic [63:0] call_values;
 function integer tick(input integer v);begin calls++;tick=v;call_values={tick,v};end endfunction
 initial begin seen=0;total=0;repeat(2)begin @pulse;seen++;total+=$time;end end
 initial begin observed=0;@immediate;observed=stage;end
 initial begin batch_count=0;repeat(3)begin @immediate;batch_count++;end end
 always @clocked always_count++;
 initial begin ticks=4;calls=0;stage=0;always_count=0;#1;
   ->> #(tick(ticks)) pulse;ticks=9;->> #1 pulse;
   ->> immediate;->> immediate;->> clocked;stage=99;
   #1;->>clocked;#4;
   if(seen!==2||total!==7||calls!==1||observed!==99||batch_count!==1||always_count!==2||pulse.triggered!==0)$fatal(1,"event NBA and delay");
   $display("TRACE nba_delay %0d %0d %0d %0d %0d %0d",seen,total,calls,observed,batch_count,always_count);$finish;
 end
endmodule
