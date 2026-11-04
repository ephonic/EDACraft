class Box;int data[];endclass
module top;
 Box selected,original,other;int calls=0,stage=0;
 function automatic Box choose();calls++;return selected;endfunction
 task automatic hold(ref int data[]);#2;data=new[2];data[0]=77;endtask
 initial begin
  original=new();other=new();original.data=new[1];other.data=new[1];other.data[0]=9;selected=original;
  fork hold(choose().data);begin #1;selected=other;end join
  stage++;$display("TRACE captured %0d %0d %0d %0d",calls,original.data.size(),original.data[0],selected.data[0]);$finish;
 end
endmodule
