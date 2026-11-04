module top;
 logic [95:0] a[],b[]; logic [3:0] c[1:0][2:0],d[4:5][6:8];
 initial begin
  a=new[1];b=new[1];a[0]=96'h80000000000000000000000x;b[0]=a[0];
  $display("TRACE unknown %b %b %b %b",a==b,a!=b,a===b,a!==b);
  b[0]=96'h80000000000000000000000z;
  $display("TRACE xz %b %b %b %b",a==b,a!=b,a===b,a!==b);
  a=new[2](a);a[1]=96'h10000000000000000;b=new[2](b);b[1]=0;
  $display("TRACE mismatch %b %b %b %b",a==b,a!=b,a===b,a!==b);
  c='{ '{4'h1,4'hx,4'h3}, '{4'h4,4'h5,4'h6}};
  d='{ '{4'h1,4'hx,4'h3}, '{4'h4,4'h5,4'h6}};
  $display("TRACE matrix %b %b",c==d,c===d);
  $display("TRACE row %b %b",c[1]===d[4],c[0]!==d[5]);
  d[5][8]=0;$display("TRACE matrix-change %b %b",c==d,c!=d);
 end
endmodule
