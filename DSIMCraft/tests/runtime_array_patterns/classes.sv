module top;
 class entry;int n;function new(input int v);n=v;endfunction endclass
 class cache #(type T=int);
  typedef T optional_data[$];
  T saved;
  function optional_data get(input bit present);if(present)return '{saved};return {};endfunction
 endclass
 cache #(entry) c;entry item;entry got[$];int observed;
 initial begin
  c=new();item=new(12);c.saved=item;got=c.get(1);
  if(got.size()!=1||got[0]!=item||got[0].n!=12)$fatal(1,"optional handle");
  observed=got[0].n;got=c.get(0);if(got.size()!=0)$fatal(1,"empty optional");
  #1;$display("TRACE classes %0d",observed);$finish;
 end
endmodule
