`timescale 1ns/1ps
package automatic p;
 function integer f();integer n=1;n++;return n;endfunction
endpackage
(* keep = 1 *) module automatic worker #(parameter BIAS=3)(output integer result);
 integer calls=0,a,b,c,d,e,f;
 function integer fresh(input integer x);integer n=BIAS;n+=x;calls++;return n;endfunction
 function static integer kept(input integer x);integer n=BIAS;n+=x;return n;endfunction
 task fresh_task;input integer x;output integer y;integer n=BIAS;begin n+=x;y=n;end endtask
 task static kept_task(input integer x,output integer y);integer n=BIAS;begin n+=x;y=n;end endtask
 initial begin
 a=fresh(2);b=fresh(2);c=kept(2);d=kept(2);fresh_task(2,e);fresh_task(2,f);
 kept_task(2,result);kept_task(2,result);
 #1;if(a!=BIAS+2||b!=BIAS+2||c!=BIAS+2||d!=BIAS+4||e!=BIAS+2||f!=BIAS+2||result!=BIAS+4||calls!=2)$fatal(1,"module defaults");
 end
endmodule
module static static_worker(output integer result);
 function integer kept();integer n=1;n++;return n;endfunction
 function automatic integer fresh();integer n=1;n++;return n;endfunction
 initial begin result=kept();result+=kept();result+=fresh();result+=fresh();end
endmodule
interface automatic auto_if;
 integer shared=0;
 function integer fresh();integer n=1;n++;shared++;return n;endfunction
 function static integer kept();integer n=1;n++;return n;endfunction
endinterface
interface static static_if;
 function integer kept();integer n=1;n++;return n;endfunction
 function automatic integer fresh();integer n=1;n++;return n;endfunction
endinterface
module top;
 integer one,two,three,a,b,c,d,e,f,g,h,i,j;
 worker #(.BIAS(3)) x(one);worker #(.BIAS(7)) y(two);static_worker z(three);
 auto_if ai();static_if si();
 function integer plain();integer n=1;n++;return n;endfunction
 initial begin
 a=ai.fresh();b=ai.fresh();c=ai.kept();d=ai.kept();e=si.kept();f=si.kept();g=si.fresh();h=si.fresh();i=plain();j=plain();
 #2;if(one!=7||two!=11||three!=9||a!=2||b!=2||c!=2||d!=3||e!=2||f!=3||g!=2||h!=2||i!=2||j!=3||ai.shared!=2||p::f()!=2||p::f()!=2)$fatal(1,"unit defaults");
 $display("TRACE defaults %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",one,two,three,a,b,c,d,e,f,g,h,i,j);
 end
endmodule
