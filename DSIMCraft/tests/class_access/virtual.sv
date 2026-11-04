module top;
 virtual class B;
  pure virtual protected function int work(int n);
  function int run(int n);return work(n)+1;endfunction
 endclass
 class D extends B;
  virtual protected function int work(int n);return n*3;endfunction
 endclass
 D d;B b;int observed;
 initial begin d=new;b=d;observed=b.run(7);$display("TRACE virtual %0d",observed);#1;$finish;end
endmodule
