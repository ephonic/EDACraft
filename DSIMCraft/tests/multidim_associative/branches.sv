module top;
 int a[int][string],b[int][string];
 int c[string];int observed;
 initial begin
 $display("TRACE absent %0d %0d %0d",a.num(),a[2].num(),a.exists(2));
 a[2]["z"]=3;a[-1]["x"]=4;a[2]["a"]=5;
 foreach(a[i,j]) $display("TRACE walk %0d %s %0d",i,j,a[i][j]);
 a[2].delete();
 $display("TRACE empty %0d %0d %0d",a.num(),a[2].num(),a.exists(2));
 b=a;b[-1]["x"]=6;
 $display("TRACE copy %0d %0d",a[-1]["x"],b[-1]["x"]);
 a[8]=c;
 $display("TRACE assignempty %0d %0d",a.exists(8),a[8].num());
 observed=b[-1]["x"];
 $finish;
 end
endmodule
