module top;
 class Key;endclass
 class Store;string values[Key];endclass
 Store a,copy;Key k;int observed=0;
 initial begin
  a=new;copy=new;k=new;a.values[k]="one";
  #2;a.values[k]="nine";observed=9;copy.values=a.values;
  #1;a.values.delete(k);a.values[k]="seven";observed=7;
  #2;if(a.values[k]!="seven"||copy.values[k]!="nine"||a.values[null]!=""||a.values.num()!=1)$fatal(1,"rollback contents");
  $display("TRACE class string rollback %0d %s",observed,a.values[k]);$finish;
 end
endmodule
