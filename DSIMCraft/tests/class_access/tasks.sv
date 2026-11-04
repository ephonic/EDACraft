module top;
 class B;
  protected int value=2;
  local task step(ref int n);#1;value+=n;n=value;endtask
  task apply(ref int n);step(n);endtask
 endclass
 class D extends B;
  protected task change(ref int n);#1;super.value+=n;n=value;endtask
  task run(ref int n);apply(n);change(n);endtask
 endclass
 D d;int observed=3;
 initial begin d=new;d.run(observed);$display("TRACE tasks %0d",observed);#1;$finish;end
endmodule
