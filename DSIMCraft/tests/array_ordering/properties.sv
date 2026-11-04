module top;
 class Entry;
  string name;int rank;
  function new(string n,int r);name=n;rank=r;endfunction
  virtual function string key();return name;endfunction
 endclass
 class Holder;
  Entry entries[$];string words[$];
  function void order();entries.sort with(item.key());words.sort();endfunction
 endclass
 Holder h;Entry e;int calls,observed;
 function automatic Holder get_holder();calls++;return h;endfunction
 initial begin
  h=new;e=new("z",1);h.entries.push_back(e);e=new("a",3);h.entries.push_back(e);e=new("m",2);h.entries.push_back(e);
  h.words='{"z","a","m"};h.order();
  if(h.entries[0].name!="a"||h.entries[2].name!="z"||h.words[0]!="a")$fatal(1,"property methods");
  get_holder().entries.rsort with(item.rank);if(calls!=1||h.entries[0].rank!=3||h.entries[2].rank!=1)$fatal(1,"receiver once");
  h.entries.reverse();if(h.entries[0].rank!=1)$fatal(1,"handle reverse");
  h.words.rsort with(item);if(h.words[0]!="z")$fatal(1,"property string key");
  observed=h.entries[1].rank+calls;$display("TRACE ordering properties %0d",observed);$finish;
 end
endmodule
