module top;
 class C;
  randc bit [2:0] a;
  rand int b;
  int limit=10;
  constraint cb {b inside {[0:limit]};}
 endclass
 C c,d;
 bit [7:0] seen,other;
 int observed;
 initial begin
  c=new;d=new;c.srandom(17);d.srandom(91);
  for(int round=0;round<3;round++)begin
   seen=0;other=0;
   for(int i=0;i<8;i++)begin
    // Unrelated constraints and seeds do not reset a live cyclic permutation.
    c.limit=i+1;c.srandom(17+i);
    if(!c.randomize()||seen[c.a]||c.b<0||c.b>c.limit)$fatal(1,"cyclic draw");
    seen[c.a]=1;observed=c.a;
    if(!d.randomize()||other[d.a])$fatal(1,"independent object");
    other[d.a]=1;
    #1;
   end
   if(seen!=8'hff||other!=8'hff)$fatal(1,"incomplete permutation");
  end
  $display("TRACE constraints cyclic permutations independent state pass");$finish;
 end
endmodule
