module top;
 class Box#(type T=int);T value;function new(T n);value=n;endfunction endclass
 function int value_or(int n,Box#(int) obj=null);if(obj==null)return n;return n+obj.value;endfunction
 task automatic exchange(ref Box#(int) obj,Box#(int) peer);
  #1;peer=obj;obj.value+=2;
 endtask
 function automatic int peek(int n,const ref Box#(int) obj);return n+obj.value;endfunction
 Box#(int) a,b;int observed;
 initial begin
  a=new(3);b=new(7);exchange(a,b);observed=value_or(4)+peek(2,b);
  $display("TRACE directions %0d %0d %0d %0d",a.value,b.value,observed,value_or(1,a));
 end
endmodule
