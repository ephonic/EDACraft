`timescale 1ns/1ps
package automatic ap;
 integer shared=10;
 function integer fresh(input integer x);
  integer n=3;begin n+=x;shared++;return n;end
 endfunction
 function static integer kept(input integer x);
  integer n=3;begin n+=x;return n;end
 endfunction
 task fresh_task(input integer x,output integer y);
  integer n=4;begin n+=x;y=n;end
 endtask
 task static kept_task(input integer x,output integer y);
  integer n=4;begin n+=x;y=n;end
 endtask
endpackage
package static sp;
 function integer kept(input integer x);integer n=2;begin n+=x;return n;end endfunction
 function automatic integer fresh(input integer x);integer n=2;begin n+=x;return n;end endfunction
endpackage
package implicit_p;
 function integer kept(input integer x);integer n=1;begin n+=x;return n;end endfunction
endpackage
module top;
 integer a,b,c,d,e,f,g,h,i,j,k,l,m,n;
 initial begin
  a=ap::fresh(2);b=ap::fresh(2);c=ap::kept(2);d=ap::kept(2);
  ap::fresh_task(2,e);ap::fresh_task(2,f);ap::kept_task(2,g);ap::kept_task(2,h);
  i=sp::kept(3);j=sp::kept(3);k=sp::fresh(3);l=sp::fresh(3);
  m=implicit_p::kept(4);n=implicit_p::kept(4);
  #1;if(a!=5||b!=5||c!=5||d!=7||e!=6||f!=6||g!=6||h!=8||i!=5||j!=8||k!=5||l!=5||m!=5||n!=9||ap::shared!=12)$fatal(1,"package lifetime");
  $display("TRACE defaults %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",a,b,c,d,e,f,g,h,i,j,k,l,m,n,ap::shared);
 end
endmodule
