`timescale 1ps/1ps
module top;
 int values[$],selected[$];
 int observed;
 initial begin
  values={1,2,1};selected=values.unique();observed=selected.size();
  #2;values.push_back(3);selected=values.unique;observed=selected.size();
  #1;values.push_back(4);selected=values.find with(item>1);observed=selected.sum();
  #2;if(selected.size()!=3 || observed!=9)$fatal(1,"locator restored storage");
  $display("TRACE locators rollback value=%0d",observed);$finish;
 end
endmodule
