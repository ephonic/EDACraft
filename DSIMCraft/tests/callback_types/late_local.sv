class Object;endclass
class Event #(type V=int) extends Object;endclass
class Callback;endclass
class UserCallback extends Callback;endclass
class Typed #(type T=Object);
 typedef Typed#(T) this_type;static this_type typed;
endclass
class Callbacks #(type T=Object,type CB=Callback) extends Typed#(T);
 typedef Callbacks#(T,CB) this_type;static this_type inst;
 static Callbacks#(T,Callback) base_inst;
 static function this_type get();
  if(inst==null) begin
   inst=new();
   if($cast(base_inst,inst))typed=base_inst;
   else begin base_inst=Callbacks#(T,Callback)::get();typed=base_inst;end
  end
  return inst;
 endfunction
endclass
class Driver;
 static function void run();
  typedef Event#(string) E;
  typedef Callbacks#(E,UserCallback) C;
  C cb;
  cb=C::get();
  $display("TRACE late %0d %0d",cb!=null,Typed#(E)::typed!=null);
 endfunction
endclass
module top;int stage=0;initial begin Driver::run();stage++;#1;Driver::run();$finish;end endmodule
