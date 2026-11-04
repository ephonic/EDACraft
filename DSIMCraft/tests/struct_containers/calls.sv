module top;
 typedef struct {string name;int id;bit[7:0] flags;} Entry;
 typedef Entry Queue[$];Queue q,result;Entry value;int observed;
 function automatic Queue transform(input Queue source);
  Queue local_queue;Entry local_value;
  if(local_value.name!=""||local_value.flags!==0||local_queue.size()!=0)return local_queue;
  local_queue=source;local_value=source[0];local_value.name="local";local_value.id+=3;local_queue.push_front(local_value);return local_queue;
 endfunction
 task automatic modify(ref Queue values,output Entry first);
  values[0].name="ref";values[0].flags='x;first=values[0];
 endtask
 initial begin
  q='{'{name:"input",id:4,flags:8'hff}};result=transform(q);
  if(result.size()!=2||result[0].name!="local"||result[0].id!=7||q[0].name!="input")$fatal(1,"input return ownership");
  modify(result,value);if(result[0].name!="ref"||value.name!="ref"||value.flags!==0||q[0].name!="input")$fatal(1,"ref output");
  result=transform(q);if(result[0].name!="local"||result.size()!=2)$fatal(1,"automatic reuse");
  observed=result[0].id+q[0].id;$display("TRACE struct calls %0d",observed);$finish;
 end
endmodule
