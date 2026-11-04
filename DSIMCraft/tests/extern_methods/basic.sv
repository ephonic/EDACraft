module top;
 class C;
  local int value;
  extern function new(int n=4);
  extern function int get(input int x=2);
  local extern function void clear(input int n=11);
  extern function void reset();
  extern task tick(input int x,output int y);
 endclass
 function C::new(int n);value=n;endfunction:new
 function int C::get(input int x=2);return value+x;endfunction:get
 task C::tick(input int x,output int y);#1;value+=x;y=value;endtask:tick
 function void C::clear(input int n);value=n;endfunction
 function void C::reset();clear();endfunction
 C a,b;int observed;
 initial begin
  a=new;b=new(20);$display("TRACE init %0d %0d",a.get(),b.get(1));
  a.tick(3,observed);$display("TRACE task %0d %0d",observed,a.get());a.reset();$display("TRACE void %0d",a.get());$finish;
 end
endmodule
