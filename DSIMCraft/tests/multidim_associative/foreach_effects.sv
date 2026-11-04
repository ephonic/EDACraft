module top;
 int a[int][string],b[int][string];int count,calls,total;
 function int idx();calls++;return 2;endfunction
 initial begin
  a[2]["a"]=10;a[2]["b"]=20;a[3]["x"]=30;
  a[idx()]["a"]+=3;
  b[idx()]=a[2];
  if(calls!=2)$fatal(1,"index evaluated more than once: %0d",calls);
  foreach(a[i,j]) begin
   if(j=="a")continue;
   count++;total+=a[i][j];
   if(i==2)a[2].delete("b");
  end
  foreach(b[i,j])begin count++;break;end
  $display("TRACE effects %0d %0d %0d %0d",calls,count,total,b[2]["a"]);
 end
endmodule
