class Item;
 int q[$];string texts[$];int data[];int map[string];int table2[int][string];
 static int shared_q[$];
endclass
module top;
 Item item;string s;int stage=0;
 initial begin
  item=new();$swrite(s,item);$display("TRACE empty <%s>",s);
  item.q='{1,-2};item.texts='{"A","B"};item.data=new[2];item.data[0]=4;item.data[1]=-5;
  item.map["Z"]=3;item.map["A"]=-4;item.table2[2]["B"]=6;item.table2[-1]["A"]=7;Item::shared_q='{8,9};
  stage++;#1;$swrite(s,item);$display("TRACE populated <%s>",s);$finish;
 end
endmodule
