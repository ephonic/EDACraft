module top;
 class Base;
  int value;
  function new; value=3; value++; endfunction
  virtual function int get; return value; endfunction
  function void clear; reset(); value+=2; endfunction
  function void reset; value=0; endfunction
  function void nop;endfunction
  extern function int external_get();
 endclass
 function int Base::external_get; return value+10; endfunction
 class Derived extends Base;
  virtual function int get; return value+100;endfunction
 endclass
 Base a,b;Derived d;
 int observed;
 initial begin
  a=new;d=new;b=d;
  if(a.get!=4 || b.get()!=104 || a.external_get()!=14)$fatal(1,"no-argument class calls");
  a.clear();a.nop();
  if(a.get()!=2 || a.external_get()!=12)$fatal(1,"multi-statement void body");
  observed=b.get();#1;$display("TRACE nonansi classes value=%0d",observed);$finish;
 end
endmodule
