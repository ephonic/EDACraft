package kinds;
 typedef int words_t[2];
 class Converter;
  typedef logic[70:0] wide_t;
  typedef enum int {FIRST=1,NEXT=2} state_t;
  extern function wide_t wide(input wide_t x);
  extern function state_t advance(input state_t x);
  extern function words_t array(input words_t x);
 endclass
 function Converter::wide_t Converter::wide(input wide_t x);return x^71'h12_3456789abcdef012;endfunction
 function Converter::state_t Converter::advance(input state_t x);return x==FIRST?NEXT:FIRST;endfunction
 function words_t Converter::array(input words_t x);words_t y;y[0]=x[1];y[1]=x[0]+2;return y;endfunction
endpackage
module top;
 import kinds::*;
 Converter c;logic[70:0] observed;words_t a,b;
 initial begin
  c=new;observed=c.wide(71'h55_123456789abcdef0);a[0]=3;a[1]=9;b=c.array(a);
  $display("TRACE types %h %s %0d %0d",observed,c.advance(Converter::FIRST).name(),b[0],b[1]);
  #1;observed=c.wide(0);$display("TRACE wide %h",observed);$finish;
 end
endmodule
