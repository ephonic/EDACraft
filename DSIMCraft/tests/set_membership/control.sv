`timescale 1ns/1ps
module top;
logic[3:0] value=0;
integer picked=0,calls=0,i=0;
logic signed[7:0] neg=-1;
function automatic[3:0] pick();begin calls++;return value;end endfunction
function automatic integer classify(input logic[3:0] x);
 begin case(x) inside [1:4]:return 10;4'b1?01:return 20;default:return 30;endcase end
endfunction
initial begin
 for(i=0;i<12;i++)begin
  #1 value=i;
  case(pick()) inside [1:4],7:picked=1;[3:8]:picked=2;4'b1?01:picked=3;default:picked=4;endcase
  if(calls!==i+1)$fatal(1,"selector repeated");
  if(picked!==((i>=1&&i<=4)||i==7?1:i>=3&&i<=8?2:i==9?3:4))$fatal(1,"first matching branch");
  if(classify(value)!==(i>=1&&i<=4?10:i==9?20:30))$fatal(1,"function case inside");
 end
 #1 value=4'bx101;
 case(value) inside 4'b0101:picked=1;4'b????:picked=2;default:picked=3;endcase
 if(picked!==2)$fatal(1,"unknown case item must not match");
 case(neg) inside 16'shffff:picked=1;32'h0:picked=2;default:picked=3;endcase
 if(picked!==3)$fatal(1,"case global context");
 assert(value inside {4'b????})else $fatal(1,"inside immediate assertion");
 #1 $display("TRACE control %0d",calls);
end
endmodule
