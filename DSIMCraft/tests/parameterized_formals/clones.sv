package boxes;
 class Box#(type T=int);T value;function new(T n);value=n;endfunction endclass
endpackage
module worker#(parameter W=8);
 function logic[W-1:0] add(int n,boxes::Box#(logic[W-1:0]) a,boxes::Box#(logic[W-1:0]) b);
  return n+a.value+b.value;
 endfunction
 boxes::Box#(logic[W-1:0]) a,b;logic[W-1:0] observed;
 initial begin a=new('1);b=new(3);observed=add(2,a,b);$display("TRACE clone %0d %h",W,observed);end
endmodule
module top;worker#(8) a();worker#(129) b();endmodule
