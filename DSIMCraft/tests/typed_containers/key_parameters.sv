module top;
 class Key;int id;function new(int n);id=n;endfunction endclass
 class Pool #(type KEY=int);
   int values[KEY];
   function int get(KEY k);return values[k];endfunction
   function void put(KEY k,int n);values[k]=n;endfunction
 endclass
 typedef int unsigned UKey;typedef string SKey;typedef Key Alias;
 Pool#(int) integers;Pool#(UKey) unsigneds;Pool#(SKey) strings;Pool#(Alias) objects;
 Key a;int ik;UKey uk;SKey sk;Alias ak;
 initial begin
  integers=new;unsigneds=new;strings=new;objects=new;a=new(7);
  integers.put(-1,11);unsigneds.put(-1,22);strings.put("alpha",33);objects.put(a,44);
  if(!integers.values.first(ik)||ik!=-1)$fatal(1,"signed type parameter");
  if(!unsigneds.values.first(uk)||uk!=32'hffffffff)$fatal(1,"unsigned type parameter");
  if(!strings.values.first(sk)||sk!="alpha")$fatal(1,"string type parameter");
  if(!objects.values.first(ak)||ak!=a)$fatal(1,"class type parameter");
  $display("TRACE parameters %0d %0d %0d %0d",integers.get(ik),unsigneds.get(uk),strings.get(sk),objects.get(ak));
 end
endmodule
