module top;
 class Holder;
  typedef string Q[$];Q words[int];
  function void seed();words[1]='{"z","a","m"};endfunction
  function void order();words[1].sort();endfunction
 endclass
 Holder h,other;int calls,observed;
 function automatic Holder receiver();calls++;return h;endfunction
 initial begin
  h=new;other=new;h.seed();h.order();receiver().words[1].push_front("first");
  if(calls!=1||h.words[1].size()!=4||h.words[1][1]!="a"||other.words.num()!=0)$fatal(1,"object state");
  h.words[2]=h.words[1];h.words[1][0]="changed";if(h.words[2][0]!="first")$fatal(1,"object copy");
  h.words[2].rsort with(item.len());if(h.words[2][0]!="first")$fatal(1,"string key");
  foreach(h.words[k,i])observed+=h.words[k][i].len();
  if(observed!=18)$fatal(1,"object foreach");$display("TRACE mixed properties %0d",observed);$finish;
 end
endmodule
