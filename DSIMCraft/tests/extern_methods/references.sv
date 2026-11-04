module top;
 class Worker;
  extern task update(ref int x,input int delta,input int hold,output int y);
  extern function int peek(const ref int x);
 endclass
 task Worker::update(ref int x,input int delta,input int hold,output int y);#hold;x+=delta;y=x;endtask
 function int Worker::peek(const ref int x);return x;endfunction
 Worker a,b;int x=5,y=10,first,second,observed;
 initial begin
  a=new;b=new;
  fork a.update(x,3,2,first);b.update(y,7,1,second);join
  observed=a.peek(x)+b.peek(y);$display("TRACE ref %0d %0d %0d %0d %0d",x,y,first,second,observed);$finish;
 end
endmodule
