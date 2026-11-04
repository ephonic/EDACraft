`timescale 1ps/1ps
module unit_test #(parameter W=8,parameter N=3) (output logic done);
class Word;
 logic [W-1:0] bits;
 function new(int n);bits=n;endfunction
 function int value();return bits;endfunction
endclass
Word p,q;
initial begin
 done=0;p=new(N);q=p;
 #N;q.bits=q.bits+1;
 $display("TRACE clone W=%0d N=%0d bits=%h value=%0d",W,N,p.bits,q.value());done=1;
end
endmodule
module top;
wire a,b;
unit_test #(8,2) u(a);
unit_test #(65,4) v(b);
initial begin wait(a&&b);#1;$finish;end
endmodule
