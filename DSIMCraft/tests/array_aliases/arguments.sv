module top;
 typedef int Q[$];typedef int Small[$:1];
 Q q,r,copy;Small narrow;
 int observed;
 task automatic mutate(ref Q dst,input Q src);#1;dst.push_back(src[0]);endtask
 task automatic replace(output Q dst);dst={7,8,9};endtask
 task automatic extend(inout Q dst);dst.push_front(4);endtask
 function automatic int peek(const ref Q src);return src[0]+src.size();endfunction
 function automatic int direct(input int src[$]);return src.size()+src[0];endfunction
 function automatic int open(input int src[]);return src.size()+src[0];endfunction
 initial begin
  q={1,2};r={3,4};copy=q;
  fork mutate(q,r);mutate(r,q);join
  $display("TRACE refs %0d %0d %0d %0d",q.size(),r.size(),q[2],r[2]);
  extend(copy);replace(r);narrow=r;
  $display("TRACE copies %0d %0d %0d %0d %0d",copy[0],r.size(),narrow.size(),peek(q),direct(q));
  observed=peek(q);$display("TRACE open %0d",open(q));#1;$finish;
 end
endmodule
