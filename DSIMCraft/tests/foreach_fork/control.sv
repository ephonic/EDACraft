`timescale 1ns/1ps
module top;
integer rounds=0,q=0,done=0,bad=0,ret=0;
task automatic walk(output integer answer);
 logic data[1:4];
 answer=0;
 foreach(data[i])begin
  if(i==2)continue;
  fork
   begin #1;q+=i;end
   begin #3;bad++;end
  join_any
  disable fork;
  answer+=i;
  if(i==3)break;
 end
 foreach(data[i])begin:outer
  foreach(data[j])begin
   if(j==1)continue;
   fork begin #1;answer+=i+j;disable outer;end begin #3;bad++;end join
  end
 end
 foreach(data[i])begin
  if(i==2)return;
  fork begin #1;done+=i;end join_none
 end
endtask
initial begin
 for(rounds=0;rounds<48;rounds++)begin walk(ret);wait fork;end
 $display("TRACE control %0d %0d %0d %0d",q,done,bad,ret);
 if(q!=192||done!=96||bad!=0||ret!=22)$fatal(1,"foreach cleanup/control");
end
endmodule
