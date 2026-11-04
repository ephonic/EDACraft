class Box;logic[7:0] data[];endclass
module top;
 Box box;int stage=0;
 function automatic void edit(ref logic[7:0] data[]);
  data[0]=8'hff;data[0][3:0]=4'ha;$display("TRACE empty %0d",data.size());
  data=new[1];data[0]=8'h12;data[2]=8'hff;data[2][3:0]=4'ha;
  $display("TRACE bounds %0d %h %h",data.size(),data[0],data[2]);
 endfunction
 initial begin box=new();edit(box.data);stage++;#1;$display("TRACE actual %0d %h",box.data.size(),box.data[0]);$finish;end
endmodule
