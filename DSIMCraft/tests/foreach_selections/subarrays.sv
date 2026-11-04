module top;
 int matrix[1:2][3:1],cube[2][2][3];
 int row,observed;
 initial begin
  foreach(matrix[i,j])matrix[i][j]=i*10+j;
  row=2;observed=0;
  foreach(matrix[row][k])observed+=matrix[row][k];
  if(observed!=66)$fatal(1,"selected row dimensions");
  foreach(cube[i,j,k])cube[i][j][k]=100*i+10*j+k;
  foreach(cube[1][,k])observed+=cube[1][1][k];
  if(observed!=399)$fatal(1,"omitted remaining dimension");
  $display("TRACE foreach subarrays observed=%0d",observed);$finish;
 end
endmodule
