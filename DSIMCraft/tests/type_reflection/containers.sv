class Global; endclass
module top;
 typedef int nums[2];
 typedef enum logic [1:0] {IDLE,DONE} state;
 typedef struct packed {int a; bit[3:0] b;} Pair;
 class Local;endclass
 class Box#(type T=int,int N=3,string S="hi");
 typedef T value_type;
 static function string name();return $typename(T);endfunction
 endclass
 int unsigned u; logic signed l; time t; bit [7:4] ba[]; int aa[string]; int bb[int];
 int q[$:5]; nums n; Local obj; Global g; Box#(Local,-2,"ok") box;
 state st; Pair pair;
 int effects;
 function automatic string effect();effects++;return "x";endfunction
 initial begin
 $display("TRACE builtin [%s] [%s] [%s] [%s] [%s]",$typename(int),$typename(logic signed[3:1]),$typename(real),$typename(string),$typename(int unsigned));
 $display("TRACE names [%s] [%s] [%s] [%s]",$typename(u),$typename(l),$typename(t),$typename(Box#(Local,-2,"ok")::value_type));
 $display("TRACE arrays [%s] [%s] [%s] [%s] [%s]",$typename(ba),$typename(aa),$typename(bb),$typename(q),$typename(n));
 $display("TRACE classes [%s] [%s] [%s]",$typename(obj),$typename(g),$typename(box));
 $display("TRACE enum [%s]",$typename(st));
 $display("TRACE struct [%s] [%s]",$typename(pair),$typename(Pair));
 $display("TRACE text [%s] [%s] %0d",$typename(effect()),$typename(aa[effect()]),effects);
 end
endmodule
