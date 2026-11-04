module top;
 class Child;
  int value;
  function new(int n);value=n;endfunction
  function void bump();value++;endfunction
 endclass
 class Holder;
  const int limit=17;
  const local Child child=new(4);
  const string name="holder";
  const real ratio=1.25;
  const int id;
  const logic [70:0] wide;
  function new(int n);
   id=n;
   wide=71'h12_3456789abcdef012;
  endfunction
  function int get();child.bump();return child.value+id+limit;endfunction
  function bit valid();return name=="holder" && ratio==1.25 && wide==71'h12_3456789abcdef012;endfunction
 endclass
 Holder a,b;
 int observed;
 initial begin
  a=new(3);b=new(9);
  if(!a.valid() || !b.valid() || a.get()!=25 || b.get()!=31 || a.get()!=26)$fatal(1,"const property values and mutable pointees");
  observed=b.id;#1;$display("TRACE const values id=%0d",observed);$finish;
 end
endmodule
