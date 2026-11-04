`timescale 1ns/1ps
module top;
integer a[1:0][2:3],index=1,seen=0,total=0;
function automatic integer sum(const ref integer words[7:6]);
 integer acc=0;foreach(words[i])acc+=words[i];return acc+$size(words)-2;
endfunction
task automatic read_words(const ref integer words[0:1],output integer result);
 #2;result=sum(words);
endtask
task automatic relay(const ref integer words[9:8],output integer result);read_words(words,result);endtask
initial begin
 a[1][2]=1;a[1][3]=2;a[0][2]=100;a[0][3]=200;
 fork relay(a[index],seen);begin #1;index=0;a[1][3]=8;end join
 total=sum(a[1]);
 $display("TRACE arrays %0d %0d %0d",seen,total,index);
 if(seen!=9||total!=9||index!=0)$fatal(1,"const ref array address capture");
end
endmodule
