module top;
 int matrix[2:1][3:1],calls,observed;int q[$];int selected_row;
 function automatic int row();calls++;return 2;endfunction
 task automatic order_ref(ref int values[$]);values.sort();endtask
 task automatic retained(ref int element);matrix[1].rsort; element=20;endtask
 initial begin
  matrix[2]='{8,1,4};matrix[1]='{9,6,3};selected_row=row();matrix[selected_row].sort with(item);
  if(calls!=1||matrix[2][3]!=1||matrix[2][2]!=4||matrix[2][1]!=8||matrix[1][3]!=9)$fatal(1,"subarray address");
  matrix[1].reverse;if(matrix[1][3]!=3||matrix[1][1]!=9)$fatal(1,"subarray reverse");
  q='{9,1,4};order_ref(q);if(q[0]!=1||q[2]!=9)$fatal(1,"queue ref");
  retained(matrix[1][3]);if(matrix[1][3]!=20||matrix[1][2]!=6||matrix[1][1]!=3)$fatal(1,"element reference identity");
  observed=matrix[2][2]+calls;$display("TRACE ordering subarrays %0d",observed);$finish;
 end
endmodule
