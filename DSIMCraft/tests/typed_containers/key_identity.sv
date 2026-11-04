module top;
 class Key; int id; function new(int v=0);id=v;endfunction endclass
 class Derived extends Key; function new(int v);super.new(v);endfunction endclass
 typedef Key Alias;
 int values[Key]; int copy_map[Alias];
 Key a,b,k,empty_key; Derived d;
 int count,total;
 initial begin
   a=new(1);b=new(2);d=new(3);
   values[a]=11;values[b]=22;values[d]=33;
   values[empty_key]=44;
   $display("TRACE size %0d null %0d %0d",values.num(),values.exists(null),values[null]);
   copy_map=values;
   if(copy_map[a]!=11 || copy_map[d]!=33)$fatal(1,"copy");
   foreach(values[index])begin count++;total+=values[index];if(index!=null && index.id<1)$fatal(1,"typed foreach");end
   $display("TRACE foreach %0d %0d",count,total);
   k=a;count=values.first(k);$display("TRACE first %0d null %0d",count,k==null);
   count=0; if(values.first(k))do begin count++;end while(values.next(k));
   $display("TRACE cursor %0d",count);
   values.delete(a);if(values.exists(a)||!copy_map.exists(a))$fatal(1,"copy isolation");
   $display("TRACE PASS");
 end
endmodule
