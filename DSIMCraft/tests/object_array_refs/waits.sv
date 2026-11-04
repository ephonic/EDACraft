class Box;int data[];endclass
module top;
 Box box;int stage=0;
 task automatic watch(const ref int data[]);wait(data.size()==3);$display("TRACE wake %0d",data.size());endtask
 initial begin
  box=new();box.data=new[1];
  fork watch(box.data);begin #1;box.data=new[3];box.data[2]=9;end join
  stage++;#1;$display("TRACE data %0d",box.data[2]);$finish;
 end
 initial begin #10;$fatal(1,"ref watcher did not wake");end
endmodule
