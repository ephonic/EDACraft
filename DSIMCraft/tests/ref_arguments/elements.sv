`timescale 1ns/1ps
module top;
integer words[2:1],index=2,calls=0;
logic[129:0] wide[1:2];
integer final_sum=0;
function automatic integer choose();calls++;return index;endfunction
task automatic edit(ref integer a,input integer amount);
 a+=amount;#2;a+=amount;
endtask
task automatic edit_wide(ref logic[129:0] a);
 a^=130'h200000000000000000000000000000001;
 #1;a+=130'h10000000000000000;
endtask
initial begin
 words[2]=10;words[1]=20;wide[1]=0;wide[2]='1;
 fork
  edit(words[choose()],5);
  begin #1;index=1;end
  edit_wide(wide[1]);
 join
 edit(words[index++],3);
 final_sum=words[2]+words[1];
 $display("TRACE elements %0d %0d %0d %0d %0d",words[2],words[1],index,calls,final_sum);
 if(words[2]!=20||words[1]!=26||index!=2||calls!=1||final_sum!=46)$fatal(1,"captured ref element address");
 if(wide[1]!==130'h200000000000000010000000000000001||wide[2]!==130'h3ffffffffffffffffffffffffffffffff)$fatal(1,"wide reference");
end
endmodule
