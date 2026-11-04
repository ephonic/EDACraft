module top;
 class C;
  local int value=3;
  protected int p=7;
  local function int twice();return 2*value;endfunction
  function void set(int n);this.value=n;endfunction
  function int compare(C other);return other.value+this.twice()+p;endfunction
 endclass
 C a,b;int observed;
 initial begin a=new;b=new;b.set(11);observed=a.compare(b);$display("TRACE basic %0d",observed);#1;$finish;end
endmodule
