class Box;int data[$:2];endclass
module top;
 Box box;int stage=0;
 function automatic void widen(ref int data[$]);
  data.push_back(3);data.push_back(4);
  $display("TRACE append %0d %0d",data.size(),data[$]);
  data='{8,7,6,5};
  $display("TRACE replace %0d %0d",data.size(),data[$]);
 endfunction
 function automatic void forward(ref int data[$:2]);widen(data);endfunction
 initial begin
  box=new();box.data='{1,2};forward(box.data);stage++;#1;
  $display("TRACE actual %0d %0d %0d",box.data.size(),box.data[0],box.data[$]);$finish;
 end
endmodule
