module top;
 typedef logic signed[64:0] wide_t;
 class Config #(W=9, N=W+1, parameter logic signed[64:0] A=-2, B=A-1,
                parameter bit[3:0] X='x, Y='z, parameter wide_t P=-5, Q=P-1,
                type T=logic[N-1:0], U=T, int K=3, L=K+2);
  T first;U second;
  function new();first='1;second='1;endfunction
  function int width_n();return $bits(first)+$bits(second)+L;endfunction
  function wide_t signed_value();return B+Q;endfunction
  function int clean();return X+Y;endfunction
 endclass
 Config a;Config#(.W(64),.K(7)) b;
 logic[64:0] observed;int width_n;
 initial begin
  a=new;b=new;observed=b.first;width_n=b.width_n();
  $display("TRACE values %0d %0d %0d %0d %h",a.width_n(),width_n,a.signed_value(),b.clean(),observed);
 end
endmodule
