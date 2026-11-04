package p;
 class Common;
  static function string type_name();return "core";endfunction
 endclass
 class Registry#(type T=int,int N=7);
  static function int create(int offset=2);return N+offset+$bits(T);endfunction
 endclass
 class Config#(type T=int,int N=3);
  typedef Registry#(T,N) type_id;
 endclass
 class Wrapper;
  typedef Common common_type;
  static function string type_name();return common_type::type_name();endfunction
 endclass
endpackage
module top;
 import p::*;
 string name;int a,b;
 initial begin
  a=Config#(int,7)::type_id::create();
  b=Config#(byte,11)::type_id::create(.offset(4));
  name={"alias:",Wrapper::type_name};
  $display("TRACE factory %0d %0d %s",a,b,name);
 end
endmodule
