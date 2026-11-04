module top;
 class Item;int value;endclass
 class Base #(parameter int W=129);
   logic[W-1:0] words[string];
   Item entries[string];int tally[int];
   function void put(string key,logic[W-1:0] value);words[key]=value;tally[-2]=tally[-2]+1;endfunction
   function logic[W-1:0] get(string key);return words[key];endfunction
 endclass
 class Derived extends Base#(129);int extra;endclass
 Base#(129) left,right;Derived child;Item one,two;string key;int ok;logic[128:0] observed,missing;
 initial begin
   child=new;left=child;right=new;one=new;one.value=17;
   left.put("x",129'h1fedcba987654321001122334455667788);left.put("z",129'h1);
   observed=child.get("x");missing=right.words["x"];
   left.entries["a"]=one;right.entries=left.entries;two=right.entries["a"];two.value=23;
   left.entries.delete("a");
   ok=left.words.first(key);$display("TRACE first %0d %s %0d",ok,key,left.words.num());
   $display("TRACE class %b %b %0d %0d %0d %0d",observed,missing,left.tally[-2],right.tally[-2],one.value,left.entries.size());
   one=right.entries["missing"];$display("TRACE handles %0d %0d %0d",one==null,right.entries["a"].value,right.entries.num());
   child.words["x"][65+:3]=3'bz1x;observed=left.words["x"];$display("TRACE selected %b",observed);
   $finish;
 end
endmodule
