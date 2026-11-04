module top;
 class Base;
  protected int values[int];
  function new();values[-4]=3;values[2]=7;values[9]=11;endfunction
  function int total();
   int sum=0;
   foreach(this.values[k])sum+=this.values[k];
   return sum;
  endfunction
 endclass
 class Derived extends Base;
  function int selected();
   int sum=0;
   foreach(super.values[k])begin
    if(k<0)continue;
    sum+=super.values[k];
   end
   return sum;
  endfunction
 endclass
 Derived c;
 int observed;
 initial begin
  c=new;
  if(c.total()!=21 || c.selected()!=18)$fatal(1,"explicit foreach receiver");
  observed=c.total();#1;$display("TRACE foreach receivers sum=%0d",observed);$finish;
 end
endmodule
