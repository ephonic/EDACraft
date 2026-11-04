`timescale 1ns/1ps
module top;
reg [79:0] words[0:2];
reg [15:0] packed_value=16'h1234;
reg [7:0] hi=8'h12,lo=8'h34;
integer probe,index=3;
function integer next;
 integer cursor=0;
 begin cursor+=1;return cursor-1;end
endfunction
function integer offset;
 integer position=4;
 begin offset=position;position+=4;return;end
endfunction
initial begin
 words[0]=80'hff;words[1]=80'h1234;words[2]=80'hffff;
 #1;words[next()]+=80'h1;words[next()]++;probe=next();
 $display("TRACE once %h %h %0d",words[0],words[1],probe);
 #1;words[1][offset()+:8]+=8'h12;
 packed_value[index+:5]^=5'h1f;
 {hi,lo}+=16'h00ff;
 $display("TRACE selects %h %h %h%h",words[1],packed_value,hi,lo);
 #1;index=17;packed_value[index-:4]|=4'hf;
 index=-1;words[index]+=next();probe=next();
 $display("TRACE bounds %h %h %0d",packed_value,words[0],probe);
 #1;$finish;
end
endmodule
