module top;
class Base #(int W=8);
 parameter int N=W+1;
 localparam int M=N+2;
 function int get();return N+M;endfunction
endclass
class Child extends Base#(16);
 localparam int EXTRA=M+1;
 function int total();return N+M+EXTRA;endfunction
endclass
class Shadow extends Base#(4);
 parameter int N=99;
 function int total();return N+M;endfunction
endclass
Child c;Shadow s;int observed;
initial begin c=new;s=new;observed=c.total();if(observed!=56||s.total()!=106||s.get()!=12||Child::N!=17)$fatal(1,"inherited constants");$display("TRACE body inheritance %0d %0d %0d",observed,s.total(),s.get());end
endmodule
