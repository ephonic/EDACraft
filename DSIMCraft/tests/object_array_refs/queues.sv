class Box;string texts[$];int bounded[$:2];endclass
module top;
 Box box;int stage=0;
 function automatic void nested(ref string data[$]);data.push_back("C");data[0]="X";endfunction
 function automatic string edit(ref string data[$],const ref string seen[$]);
  nested(data);return {seen[0],"/",seen[1],"/",seen[2]};
 endfunction
 function automatic void bound(ref int data[$:2]);data.push_back(3);data.push_back(9);data.sort();data[0][7:0]=10;endfunction
 initial begin
  box=new();box.texts='{"A","B"};box.bounded='{5,2};
  $display("TRACE text %s",edit(box.texts,box.texts));bound(box.bounded);stage++;#1;
  $display("TRACE bound %0d %0d %0d %0d",box.bounded.size(),box.bounded[0],box.bounded[1],box.bounded[2]);$finish;
 end
endmodule
