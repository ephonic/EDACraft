module top;
 string q[$];logic [15:0] bits; string s;int calls;
 class C;
 string words[$];
 function new();words.push_back("class");words.push_back("words");endfunction
 endclass
 C c;
 function automatic string queue_join(ref string items[$]);return {>>{items}};endfunction
 function automatic string text();calls++;return "!";endfunction
 initial begin
 s=queue_join(q);$display("TRACE empty [%s]",s);
 q.push_back("uvm");q.push_back("");q.push_back("_");q.push_back("join");
 s=queue_join(q);$display("TRACE queue [%s] %0d",s,q.size());
 s={>>{q,text(),"?"}};$display("TRACE mixed [%s] %0d",s,calls);
 bits={>>{"AB"}};$display("TRACE packed %h",bits);
 c=new();s={>>{c.words}};$display("TRACE object [%s]",s);
 end
endmodule
