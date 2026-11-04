module top;
 class Store;int values[string];endclass
 Store item;int map[string];int observed,history;
 initial begin
  item=new;map[""]=1;item.values["v"]=2;observed=map[""]+item.values["v"];
  #2;map[""]=5;item.values["v"]=7;observed=map[""]+item.values["v"];
  #2;item.values.delete("v");map["late"]=11;observed=map[""]+item.values["v"];history=map.size();
  #2;item.values["v"]=13;observed=map["late"]+item.values["v"];
  #1;$display("TRACE rollback %0d %0d %0d",observed,history,item.values.num());$finish;
 end
endmodule
