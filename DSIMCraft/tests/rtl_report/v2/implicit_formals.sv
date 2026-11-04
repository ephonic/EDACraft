`timescale 1ns/1ps
module top;
 typedef struct packed {logic[7:0]a;logic[7:0]d;logic w;} req_t;
 typedef enum logic[1:0]{A=1,B=2} mode_t;
 req_t r,other,copied;logic[16:0] value;
 function automatic logic[16:0] pack(req_t q);
  return {q.a,q.d,q.w};
 endfunction
 function automatic req_t copy(req_t q);return q;endfunction
 function automatic logic[16:0] choose(req_t q,second,input logic select_first);
  return pack(select_first?q:second);
 endfunction
 function automatic integer code(mode_t m);return int'(m);endfunction
 task automatic echo(req_t q,output logic[16:0]result);
  begin #1;result=pack(q);end
 endtask
 initial begin
  r.a=8'ha5;r.d=8'hff;r.w=1;other=0;
  copied=copy(r);
  if(copied!==r||pack(r)!==17'h14bff||choose(r,other,1)!==17'h14bff||choose(r,other,0)!==0||code(B)!==2)$fatal(1,"implicit typed function input");
  echo(r,value);if(value!==17'h14bff)$fatal(1,"implicit typed task input");
  $display("TRACE implicit named struct and enum formals pass");
 end
endmodule
