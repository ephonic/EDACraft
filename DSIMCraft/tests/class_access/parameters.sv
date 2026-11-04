module top;
 class Box #(type T=int,parameter int V=1);
  local static int count=V;
  protected T data;
  static local function int next_id();count++;return count;endfunction
  function new(T value);data=value;endfunction
  static function Box #(T,V) create(T value);Box #(T,V) h;h=new(value+next_id());return h;endfunction
  function T get();return data;endfunction
 endclass
 Box #(int,2) a,b;Box #(int,8) c;int observed;
 initial begin a=Box #(int,2)::create(10);b=Box #(int,2)::create(10);c=Box #(int,8)::create(10);observed=a.get()+b.get()+c.get();$display("TRACE parameters %0d %0d %0d %0d",a.get(),b.get(),c.get(),observed);#1;$finish;end
endmodule
