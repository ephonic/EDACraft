module top;
class C;
 parameter A=3, B=A+2;
 localparam int N=B*2;
 bit[N-1:0] data;
 function int get(int x=N);return A+B+$bits(data)+x;endfunction
endclass
C a;int observed;
initial begin a=new;observed=a.get();if(observed!=28 || C::A!=3 || C::N!=10)$fatal(1,"class constants");$display("TRACE body basic %0d %0d",observed,C::B);end
endmodule
