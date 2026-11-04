`timescale 1ps/1ps
module leaf;
  integer n;
  initial begin : empty_list
    ; ; (* keep=1 *) ;
    n=0;
    begin ; ; end
  end
endmodule
module top;
  leaf u();
  integer value,i;
  function automatic integer f(input integer a);
    ; ;
    begin ; end
    return a+1;
    ;
  endfunction
  task automatic t;
    ;
    u.n=f(8);
    ;
  endtask
  initial begin
    ; ;
    value=0;
    #1;t();
    for(i=0;i<3;i=i+1)begin ;value=value+1;;end
    if(1)begin ;end else ;
    case(value)3:begin ; ;end default:$fatal(1,"empty statement case");endcase
    fork ; begin ;#1;value=value+1;;end join
    ;
    if(value!=4||u.n!=9)$fatal(1,"null statement execution");
    $display("TRACE hierarchy nulls %0d %0d",value,u.n);
    $finish;
  end
endmodule
