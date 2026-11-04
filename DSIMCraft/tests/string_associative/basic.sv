module top;
  int aa[string]; string k; int result;
  class C;
    int d[string];
    function int inc(string key);d[key]=d[key]+1;return d[key];endfunction
  endclass
  C a,b;
  initial begin
    aa["z"]=7;aa["a"]=3;aa[""]=9;
    result=aa.first(k);$display("TRACE first %0d <%s> %0d %0d",result,k,aa[k],aa.num());
    result=aa.next(k);$display("TRACE next %0d <%s> %0d",result,k,aa[k]);
    a=new;b=new;result=a.inc("x");result=a.inc("x");
    $display("TRACE class %0d %0d %0d %0d",a.d["x"],b.d["x"],a.d.num(),b.d.num());
    a.d["x"][7:0]=8'hff;
    result=a.d.first(k);$display("TRACE member %0d <%s> %0d",result,k,a.d[k]);
    a.d.delete("x");$display("TRACE delete %0d",a.d.size());
    $finish;
  end
endmodule
