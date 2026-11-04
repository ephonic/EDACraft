module top;
 typedef int queue_t[$];
 int values[4]='{3,1,3,2};
 int words[2]='{32'h42,16'h4142};
 queue_t selected;
 int observed;
 function automatic queue_t larger(input int threshold);
  return values.find(x) with(x>threshold);
 endfunction
 function automatic int total(input queue_t data);return data.sum;endfunction
 initial begin
  selected=larger(1);if(selected.size()!=3 || selected.sum()!=8)$fatal(1,"locator queue return");
  observed=total(values.unique());if(observed!=6)$fatal(1,"locator as array argument");
  selected=words.min with(string'(item));if(selected.size()!=1 || selected[0]!=16'h4142)$fatal(1,"string key ordering");
  #1;$display("TRACE locators functions total=%0d",observed);$finish;
 end
endmodule
