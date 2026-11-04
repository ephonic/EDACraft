`timescale 1ns/1ps
module top;
 integer result=0,calls=0;
 function automatic integer measure(input integer x);
  string text="function";
  text={text,"!"};return text.len()+x;
 endfunction
 task automatic work(input integer id);
  string local_text="task",copy;
  if(local_text!="task"||copy!="") $fatal(1,"automatic reset");
  if(id==1)local_text={local_text,"one"};else local_text={local_text,"two!"};
  copy=local_text;#1;
  if(local_text!=copy||local_text.len()!=6+id) $fatal(1,"automatic overlap");
  result=result+measure(local_text.len());calls=calls+1;
 endtask
 initial begin
  fork work(1);work(2);join
  work(1);
  if(result!=49||calls!=3) $fatal(1,"automatic result");
  $display("TRACE automatic %0d %0d",result,calls);#0.25;$finish;
 end
endmodule
