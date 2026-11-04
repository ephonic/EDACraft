class Guard;
 static Guard pending[$];
 int value,seen=0;
 function new(int value);this.value=value;endfunction
 function void watch();
  fork begin #2;seen=value;end join_none
 endfunction
 static function void launch();
  fork begin
   forever begin
    Guard next_guard;
    wait(pending.size()!=0);next_guard=pending.pop_front();next_guard.watch();
   end
  end join_none
 endfunction
endclass
module top;
 Guard a,b;int stage=0;
 initial begin
  a=new(11);b=new(22);Guard::launch();
  #1;Guard::pending.push_back(a);Guard::pending.push_back(b);
  #4;$display("TRACE guard %0d %0d %0d",a.seen,b.seen,Guard::pending.size());
  stage++;$finish;
 end
endmodule
