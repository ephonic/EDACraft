module top;
 class C#(type T=int,parameter int W=8);T value;function new(T n);value=n;endfunction endclass
 function automatic C#(logic[64:0],9) bounce(input C#(.W(9),.T(logic[64:0])) p);
  C#(logic[64:0],9) local_value;local_value=p;return local_value;
 endfunction
 task automatic bump(ref C#(logic[64:0],9) p);p.value=p.value+1;endtask
 C#(logic[64:0],9) a,b;logic[64:0] observed;
 initial begin a=new(65'h1fffffffffffffffe);b=bounce(a);bump(b);observed=a.value;$display("TRACE signatures %h",observed);end
endmodule
