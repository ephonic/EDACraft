module top;
 class C;
  const int n;
  function new(int count);
   for(int i=0;i<count;i++)n=0;
  endfunction
 endclass
 C c;
 initial begin c=new(2);$fatal(1,"duplicate assignment escaped");end
endmodule
