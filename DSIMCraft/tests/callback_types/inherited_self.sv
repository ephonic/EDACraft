class Object;int value=3;endclass
class Child extends Object;endclass
class Callback;endclass
class UserCallback extends Callback;endclass
class Typed #(type T=Object);
 typedef Typed#(T) this_type;
 static this_type typed;
endclass
class Callbacks #(type T=Object,type CB=Callback) extends Typed#(T);
 typedef Callbacks#(T,CB) this_type;
 static this_type inst;
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
module top;
 Callbacks#(Child,UserCallback) cb;Typed#(Child) typed;int stage=0;
 initial begin
  cb=Callbacks#(Child,UserCallback)::get();typed=Typed#(Child)::typed;
  $display("TRACE handles %0d %0d",cb!=null,typed!=null);stage++;#1;
  $display("TRACE shared %0d",typed==Callbacks#(Child,Callback)::base_inst);$finish;
 end
endmodule
