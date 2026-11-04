module top;
 class Key;endclass
 class Base;string rights[Key];endclass
 class Child extends Base;string paths[string][Key];string numbered[int];endclass
 Child a,b;Base base_handle;Key k;string route;int seen;
 initial begin
  a=new;b=new;k=new;base_handle=a;
  a.rights[k]="RW";a.paths["bus"][k]="root";a.numbered[-2]="negative";
  b.rights=a.rights;b.paths=a.paths;b.numbered=a.numbered;
  b.rights[k]="RO";b.paths["bus"][k]="branch";
  if(base_handle.rights[k]!="RW"||b.rights[k]!="RO"||a.paths["bus"][k]!="root"||b.paths["bus"][k]!="branch"||b.numbered[-2]!="negative")$fatal(1,"deep copy/inheritance");
  if(b.paths["none"][k]!=""||b.paths["none"].num()!=0||b.paths.num()!=1)$fatal(1,"nested default no insertion");
  foreach(b.paths[x,y])begin route={x,":",b.paths[x][y]};seen++;end
  if(route!="bus:branch"||seen!=1)$fatal(1,"nested foreach");
  b.paths["bus"].delete(k);if(b.paths["bus"][k]!=""||a.paths["bus"][k]!="root")$fatal(1,"leaf deletion");
  $display("TRACE class string copy %0d %s",seen,route);$finish;
 end
endmodule
