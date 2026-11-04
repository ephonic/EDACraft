module top;
 logic choice;
 logic [7:0] left_value=8'ha5,right_value=8'ha3,merged;
 logic signed [7:0] negative_value=-2;
 logic signed [15:0] extended;
 int count=0;
 logic signed [31:0] selected;
 function automatic int mark(input int v);count++;return v;endfunction
 initial begin
  choice=1;selected=choice?mark(5):mark(7);
  if(selected!=5||count!=1)$fatal(1,"true branch");
  extended=choice?negative_value:8'sd3;
  if(extended!=-2)$fatal(1,"conditional sign extension");
  choice=0;selected=choice?mark(5):mark(7);
  if(selected!=7||count!=2)$fatal(1,"false branch");
  choice=1'bx;selected=choice?mark(5):mark(7);
  merged=choice?left_value:right_value;
  if(count!=4||selected!==32'b000000000000000000000000000001x1||merged!==8'b10100xx1)$fatal(1,"unknown merge");
  $display("TRACE conditional %0d %b %b %0d",count,selected,merged,extended);
  $finish;
 end
endmodule
