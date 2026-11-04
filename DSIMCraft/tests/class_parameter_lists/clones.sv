module worker #(parameter W=8);
 typedef logic[W-1:0] word_t;
 class C #(type T=word_t, U=T, int N=W, M=N+1);
  T a;U b;
  function new();a='1;b='1;endfunction
  function int width_n();return $bits(a)+$bits(b)+M;endfunction
 endclass
 C normal;C#(.T(word_t),.U(word_t),.N(W),.M(W+1)) same;
 logic[W-1:0] observed;
 initial begin normal=new;same=normal;observed=same.a;$display("TRACE clone %0d %0d %h",W,same.width_n(),observed);end
endmodule
module top;worker#(8) a();worker#(129) b();endmodule
