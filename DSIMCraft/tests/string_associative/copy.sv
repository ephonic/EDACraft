module top;
 class C;int a[string];endclass
 C one,two;int a[string],b[string];
 logic[7:0] raw[string];bit[7:0] clean[string];
 class Store;bit[7:0] values[string];endclass
 Store item;
 initial begin
 one=new;two=new;
 one.a["x"]=9;two.a=one.a;one.a["x"]=3;a=two.a;b=a;a.delete();
 $display("TRACE copy %0d %0d %0d %0d",one.a["x"],two.a["x"],b["x"],a.num());
 raw["k"]=8'bz10x0110;clean=raw;item=new;item.values=raw;
 $display("TRACE states %b %b",clean["k"],item.values["k"]);
 $finish;
 end
endmodule
