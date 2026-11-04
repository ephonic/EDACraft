module top;
 typedef enum logic[3:0] {ONE=1,NINE=9} Four;
 typedef enum {THREE=3,SEVEN=7} Two;
 class Item;int n;endclass
 Four four[$],fa[int],fd[];Two two[$],ta[int],td[];Item objects[$],oa[int],od[],v;
 logic[3:0] observed;int nulls;
 initial begin
  fd=new[1];td=new[1];od=new[1];v=objects.pop_front();
  observed=four.pop_back();nulls=(v==null)+(oa[-9]==null)+(od[0]==null);
  $display("TRACE defaults %h %h %h %0d %0d %0d %0d",observed,fa[9],fd[0],two.pop_back(),ta[-9],td[0],nulls);
 end
endmodule
