module child #(parameter W=65)(output int observed);
 typedef bit[W-1:0] key_t;
 typedef enum bit[7:0] {SMALL=1,LARGE=250} axis_t;
 typedef int inner_t[axis_t];typedef inner_t outer_t[key_t];
 outer_t a,b;inner_t leaf;key_t high;axis_t k,indices[$];
 initial begin
  high='1;a[high][LARGE]=9;a[0][SMALL]=4;b=a;leaf=a[high];
  a[high].delete();a[high]=leaf;
  if(!a[high].first(k)||k!=LARGE)$fatal(1,"inner enum cursor");
  indices=a[high].find_index() with(item>5);
  if(indices.size()!=1||indices[0]!=LARGE)$fatal(1,"inner locator");
  observed=0;
  foreach(b[i,j])begin if($bits(i)!=W||$bits(j)!=8)$fatal(1,"axis widths");observed+=b[i][j];end
  b[high][LARGE][3:0]=3;
  if(b[high][LARGE]!=3||a[high][LARGE]!=9)$fatal(1,"packed write/copy");
 end
endmodule
module top;int x,y;child#(65) a(x);child#(129) b(y);
 initial begin #1;$display("TRACE typed axes %0d %0d",x,y);end
endmodule
