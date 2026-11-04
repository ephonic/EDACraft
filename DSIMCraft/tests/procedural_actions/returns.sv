`timescale 1ns/1ps
module top;
integer result=0,count=0,nba_value=0,outer=0,answer=0;
reg pulse=0;
reg signed [79:0] wide=0;
function signed [79:0] calculate(input integer limit);
 reg signed [79:0] total;
 begin
  total=0;
  for(int i=0;i<8;i+=1)begin
   if(i==limit)return total-80'sd3;
   total+=i;
  end
  return -80'sd99;
  calculate=80'sd999;
 end
endfunction
task inner(input integer mode,output integer value,inout integer tally);
 begin
  value=10;tally+=1;
  if(mode==0)return;
  #1;value+=5;
  if(mode==1)return;
  @(posedge pulse);value+=7;
  for(int j=0;j<3;j+=1)begin
   tally+=2;
   if(j==1)return;
  end
  value=999;
 end
endtask
task wrapper(output integer value);
 integer local_tally=0;
 begin
  inner(0,value,local_tally);outer+=1;
  #1;value+=3;return;
  outer=99;
 end
endtask
task queued;
 begin nba_value<=#2 42;#1;return;nba_value<=99;end
endtask
initial begin
 #1;wide=calculate(4);$display("TRACE function %h",wide);
 inner(0,result,count);$display("TRACE immediate %0d %0d",result,count);
 inner(1,result,count);$display("TRACE delayed %0d %0d",result,count);
 inner(2,result,count);$display("TRACE event %0d %0d",result,count);
 wrapper(answer);$display("TRACE nested %0d %0d",answer,outer);
 queued();#2;$display("TRACE nba %0d",nba_value);
 #1;wide=calculate(9);$display("TRACE fallback %h",wide);$finish;
end
initial begin #5;pulse=1;end
endmodule
