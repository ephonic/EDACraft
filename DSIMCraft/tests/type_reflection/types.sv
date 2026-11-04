package p;
  typedef logic signed [3:0][7:0] word;
  typedef int alias_int;
  typedef enum {A,B} state;
  class C; endclass
  class Box #(type T=int, int N=3);
    static function string type_name(); return $typename(T); endfunction
  endclass
endpackage
module top;
 import p::*;
 int i; integer j; bit b; logic l; reg r;
 logic signed [3:0][7:0] vec;
 word w;
 int a[2:4]; int q[$]; string s; real x; chandle h;
 state st; C c; Box#(C,7) bc;
 function int effect();i++;return 1;endfunction
 initial begin
  $display("TRACE builtins [%s] [%s] [%s] [%s] [%s]",$typename(i),$typename(j),$typename(b),$typename(l),$typename(r));
  $display("TRACE vec [%s] [%s] [%s]",$typename(vec),$typename(w),$typename(word));
  $display("TRACE arr [%s] [%s] [%s]",$typename(a),$typename(q),$typename(a[2]));
  $display("TRACE other [%s] [%s] [%s] [%s]",$typename(s),$typename(x),$typename(h),$typename(st));
  $display("TRACE cls [%s] [%s] [%s] [%s]",$typename(c),$typename(C),$typename(bc),Box#(word)::type_name());
  $display("TRACE expr [%s] [%s] [%s] [%s]",$typename(1),$typename(8'hff),$typename("hi"),$typename(effect()));
  $display("TRACE side %0d",i);
  $finish;
 end
endmodule
