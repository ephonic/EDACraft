module leaf #(parameter int N=2)(output int observed);
 class Store #(type T=string);
  T q[$];
  function void add(T value);q.push_back(value);endfunction
 endclass
 Store #(string) a,b;string copy[$];
 initial begin
  a=new();b=new();for(int i=0;i<N;i++)a.add($sformatf("value%0d",i));
  b.q=a.q;copy=b.q;a.q.delete();
  if(copy.size()!=N||b.q.size()!=N||a.q.size()!=0||copy[0]!="value0")$fatal(1,"clone strings");
  observed=copy.size();
 end
endmodule
module top;
 int a,b;leaf #(2) first(a);leaf #(4) second(b);
 initial begin #1;if(a!=2||b!=4)$fatal(1,"clone outputs");$display("TRACE clones %0d %0d",a,b);$finish;end
endmodule
