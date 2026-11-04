class Builder;
 string line;
 function void fill(input int count,input string word);line={count{word}};endfunction
 function string get(input int count);return {count{"!"}};endfunction
endclass
module top;
 Builder item;string lines[$];int stage=0;
 initial begin
  item=new();item.fill(3,"uv");lines.push_back(item.get(4));lines.push_back({2{item.line}});
  $display("TRACE object %s",item.line);$display("TRACE queue %s %s",lines[0],lines[1]);
  stage++;#1;$finish;
 end
endmodule
