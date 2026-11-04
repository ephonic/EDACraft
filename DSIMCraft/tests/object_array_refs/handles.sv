class Payload;int tag;function new(int n);tag=n;endfunction endclass
class Box;Payload data[];endclass
module top;
 Box box;Payload first,second;int stage=0;
 function automatic void resize(ref Payload target[],const ref Payload seen[]);
  target=new[3](seen);target[1].tag=17;
  $display("TRACE refs %0d %0d %0d",seen.size(),seen[0].tag,seen[1].tag);
 endfunction
 initial begin
  box=new();first=new(3);second=new(5);box.data=new[2];box.data[0]=first;box.data[1]=second;
  resize(box.data,box.data);stage++;#1;
  $display("TRACE handles %0d %0d %0d",box.data.size(),second.tag,box.data[2]==null);$finish;
 end
endmodule
