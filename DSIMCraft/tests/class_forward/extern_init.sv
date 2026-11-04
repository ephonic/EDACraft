`timescale 1ps/1ps
package p;
  typedef class Reporter;
  function automatic int invoke();
    Reporter r;
    r=new;
    return r.value();
  endfunction
  class Client;
    extern static function int read();
    typedef int result_t;
  endclass
  function int Client::read();
    result_t n=invoke();
    int m=n+5;
    return m;
  endfunction
  typedef class Handler;
  class Reporter;
    Handler h;
    function int value();h=new;return h.value;endfunction
  endclass
  class Handler;int value=23;endclass
endpackage
module top;
  int observed;
  initial begin observed=p::Client::read();#1;$display("TRACE %0d",observed);end
endmodule
