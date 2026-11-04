module top;
class C #(parameter int W=8,type T=logic[W-1:0]);
 parameter int A=W+1;
 localparam int N=A+2;
 localparam int TW=$bits(T);
 bit[N-1:0] data;
 function int get();return C::A+N+TW+$bits(data);endfunction
endclass
C a;C#(16) b;typedef C#(16) Other;int observed;
localparam int WIDTH=C#(16)::N;
bit[WIDTH-1:0] external_data;
initial begin a=new;b=new;observed=b.get();if(a.get()!=39||observed!=71||$bits(external_data)!=19||Other::A!=17)$fatal(1,"specialized constants");$display("TRACE body specializations %0d %0d %0d",a.get(),observed,C#(16)::N);end
endmodule
