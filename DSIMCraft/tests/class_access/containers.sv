module top;
 class C;
  local int q[int];
  protected int aa[string];
  local logic [128:0] wide=129'h100000000000000000000000000000005;
  function void put(string key,int n);q[0]=n;aa[key]=n+2;endfunction
  function int read(C other,string key);return other.q[0]+other.aa[key]+int'(other.wide);endfunction
 endclass
 C a,b;int observed;
 initial begin a=new;b=new;b.put("",11);observed=a.read(b,"");$display("TRACE containers %0d",observed);#1;$finish;end
endmodule
