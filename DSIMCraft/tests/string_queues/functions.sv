module top;
 typedef string strings_t[$];
 strings_t q,r;int observed;
 function automatic strings_t decorate(input strings_t source);
  strings_t local_q;local_q=source;local_q.push_front("prefix");return local_q;
 endfunction
 function automatic void append(ref strings_t target,input string text);target.push_back(text);endfunction
 task automatic transfer(input strings_t source,output strings_t target);target=source;target.push_back("task");endtask
 initial begin
  q='{"first","second"};r=decorate(q);append(q,"third");transfer(r,q);
  if(q.size()!=4||q[0]!="prefix"||q[3]!="task"||r.size()!=3)$fatal(1,"function queues");
  observed=q.size()+r.size();$display("TRACE functions %s %s %0d",q[1],q[3],observed);$finish;
 end
endmodule
