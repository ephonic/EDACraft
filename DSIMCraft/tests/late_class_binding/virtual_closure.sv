package pkg;
 virtual class Init;pure virtual function int initialize();endclass
 Init pending[$];
 class Leaf#(type T=int) extends Init;
  static Leaf#(T) cached=get();
  static function Leaf#(T) get();if(cached==null)begin cached=new;pending.push_back(cached);end return cached;endfunction
  static function int value();return 1;endfunction
  virtual function int initialize();return $bits(T)+1;endfunction
 endclass
 class Registry#(type T=int) extends Init;
  static Registry#(T) cached=get();
  static function Registry#(T) get();if(cached==null)begin cached=new;pending.push_back(cached);end return cached;endfunction
  virtual function int initialize();return Leaf#(T)::value();endfunction
 endclass
 function automatic int run_all();int result;foreach(pending[i])result+=pending[i].initialize();return result;endfunction
endpackage
module top;import pkg::*;Registry#(bit[47:0]) r;int observed;initial begin r=Registry#(bit[47:0])::get();observed=run_all();$display("TRACE virtual closure %0d %0d",observed,pending.size());end endmodule
