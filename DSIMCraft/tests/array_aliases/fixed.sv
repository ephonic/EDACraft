module top;
 typedef bit[8:0] Elem;
 typedef Elem Row[2:0];
 typedef Row Grid[0:1];
 typedef Grid Alias;
 Alias saved;Row row;
 function automatic Row make(input int n);
  Row local_row;foreach(local_row[i])local_row[i]=n+i;return local_row;
 endfunction
 function automatic Grid make_grid(input int n);
  Grid local_grid;foreach(local_grid[i,j])local_grid[i][j]=n+10*i+j;return local_grid;
 endfunction
 function automatic int sum(input Row x);return x[0]+x[1]+x[2];endfunction
 initial begin
  saved=make_grid(5);saved[1]=make(20);row=make(10);
  $display("TRACE fixed %0d %0d %0d %0d %0d",saved[0][2],saved[1][0],row[2],sum(make(30)),$bits(saved));
  #1;saved=make_grid(40);$display("TRACE grid %0d %0d",saved[0][0],saved[1][2]);#1;$finish;
 end
endmodule
