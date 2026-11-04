class Box;int data[];endclass
module top;
 Box box;int stage=0;
 function automatic void edit(ref int left[],ref int right[]);
  left=new[3];left[0]=11;right[1]=22;right=new[2](right);right[0]=33;
  $display("TRACE inside %0d %0d %0d",left.size(),left[0],left[1]);
 endfunction
 initial begin
  box=new();box.data=new[1];edit(box.data,box.data);stage++;#1;
  $display("TRACE after %0d %0d %0d",box.data.size(),box.data[0],box.data[1]);$finish;
 end
endmodule
