`timescale 1ns/1ps
module top;
logic[1:0] a,b;
logic eq,ne,member;
integer i=0,j=0,count=0;
function automatic bit4(input integer code);
 begin case(code&3) 0:return 1'b0;1:return 1'b1;2:return 1'bx;default:return 1'bz;endcase end
endfunction
function automatic integer reference(input logic[1:0] left,input logic[1:0] right);
 integer k,unknown_bit=0,mismatch=0;
 begin
  for(k=0;k<2;k++)begin
   if(right[k]!==1'bx&&right[k]!==1'bz)begin
    if(left[k]===1'bx||left[k]===1'bz)unknown_bit=1;
    else if(left[k]!==right[k])mismatch=1;
   end
  end
  if(mismatch)return 0;if(unknown_bit)return -1;return 1;
 end
endfunction
initial begin
 for(i=0;i<16;i++)for(j=0;j<16;j++)begin
  #1 a={bit4(i>>2),bit4(i)};b={bit4(j>>2),bit4(j)};
  eq=a==?b;ne=a!=?b;member=a inside {b};
  if(reference(a,b)==-1)begin if(eq!==1'bx||ne!==1'bx||member!==1'bx)$fatal(1,"unknown wildcard");end
  else if({31'b0,eq}!==reference(a,b)||ne!==(~eq)||member!==eq)$fatal(1,"wildcard truth table");
  count++;
 end
 $display("TRACE wildcard %0d",count);
end
endmodule
