module top;
 class Counter;
  int value;
  extern function int add(input int x=3);
  extern task delayed(input int x,output int y);
 endclass
 function int Counter::add;
  input int x;
  int intermediate;
  begin intermediate=x+1;value+=intermediate;add=value;end
 endfunction
 task Counter::delayed;
  input int x;output int y;
  int z;
  begin z=x+2;#1;value+=z;y=value;end
 endtask
 Counter c;int observed;
 initial begin
  c=new;c.value=2;observed=c.add();$display("TRACE nonansi %0d",observed);
  c.delayed(5,observed);$display("TRACE delayed %0d",observed);$finish;
 end
endmodule
