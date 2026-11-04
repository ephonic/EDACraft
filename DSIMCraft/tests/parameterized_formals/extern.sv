module top;
 class Box#(type T=int);T value;function new(T n);value=n;endfunction endclass
 class Service#(type T=int);
  T value;
  extern function void store(int n,Box#(T) obj,Box#(T) peer=null);
  extern function T get();
 endclass
 function void Service::store(int n,Box#(T) obj,Box#(T) peer);
  value=obj.value+n;if(peer!=null)value+=peer.value;
 endfunction
 function Service::T Service::get();return value;endfunction
 Service#(logic[64:0]) service;Box#(logic[64:0]) a,b;
 logic[64:0] observed;
 initial begin
  service=new;a=new(65'h10000000000000000);b=new(6);
  service.store(3,a,b);observed=service.get();
  $display("TRACE extern %h",observed);
  service.store(5,a);$display("TRACE default %h",service.get());
 end
endmodule
