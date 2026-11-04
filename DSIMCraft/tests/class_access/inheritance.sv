module top;
 int outer=40;
 class B;
  local int value=2;
  local int outer=3;
  protected int p=5;
  local function int hidden();return value+outer;endfunction
  function int base_read();return hidden()+p;endfunction
 endclass
 class D extends B;
  local int value=17;
  function int derived_read(B other);return value+other.p+outer;endfunction
  function void bump();super.p+=3;endfunction
 endclass
 B b;D d;int observed;
 initial begin b=new;d=new;d.bump();observed=d.base_read()+d.derived_read(b);$display("TRACE inherited %0d %0d %0d",d.base_read(),d.derived_read(b),observed);#1;$finish;end
endmodule
