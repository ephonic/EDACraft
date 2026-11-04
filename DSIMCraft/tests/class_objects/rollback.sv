`timescale 1ps/1ps
module top;
class State;
 int value=1;
 logic [128:0] bits=129'h5;
 function new(int n=1);value=n;endfunction
 function int bump(int n);value+=n;bits[67:64]=n;return value;endfunction
endclass
State p,q;
int result;
initial begin
 p=new(4);q=p;
 #2;result=p.bump(3);
 #2;q=new(9);result=q.bump(1);
 #2;p.value=17;
 $display("TRACE rollback t=%0t p=%0d q=%0d bits=%h r=%0d",$time,p.value,q.value,p.bits,result);
 #2;$finish;
end
endmodule
