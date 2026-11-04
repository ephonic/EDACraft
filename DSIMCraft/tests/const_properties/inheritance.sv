module top;
 class Base;
  protected const int id;
  const int base_limit=5;
  function new(int n);id=n;endfunction
  virtual function int get();return id+base_limit;endfunction
 endclass
 class Derived extends Base;
  local const int extra;
  function new(int n);super.new(n);extra=n+1;endfunction
  virtual function int get();return super.get()+extra;endfunction
 endclass
 Base a;Derived d;
 int observed;
 initial begin
  d=new(7);a=d;
  observed=a.get();if(observed!=20)$fatal(1,"inherited constructor constants");
  #1;$display("TRACE const inheritance value=%0d",observed);$finish;
 end
endmodule
