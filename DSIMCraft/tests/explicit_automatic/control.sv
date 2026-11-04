`timescale 1ns/1ps
module top;
integer rounds=0,q=0,done=0,bad=0;
initial begin
 for(rounds=1;rounds<=48;rounds++)begin:body
  automatic integer saved=rounds;
  integer calls=0;
  fork
   begin #1;q+=saved;end
   begin #4;bad++;end
  join_any
  disable fork;
  calls++;done++;
  if(saved!=rounds||calls!=done)$fatal(1,"mixed lifetime block");
  repeat(2)begin
   automatic integer value=saved;
   if(value%2)continue;
   if(value>10)break;
   q+=value;
  end
  begin:escape
   automatic integer value=saved;
   if(value>0)disable escape;
   bad++;
  end
 end
 $display("TRACE control %0d %0d %0d",q,done,bad);
 if(q!=1236||done!=48||bad!=0)$fatal(1,"automatic scope cleanup");
end
endmodule
