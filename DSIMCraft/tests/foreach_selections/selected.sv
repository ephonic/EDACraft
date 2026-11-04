module top;
 class Cell;
  int values[int];
  int labels[string];
 endclass
 Cell nodes[],queue[$],fixed_nodes[2];
 int choice,calls,observed;
 function automatic int pick();calls++;return choice;endfunction
 initial begin
  nodes=new[2];nodes[0]=new;nodes[1]=new;
  nodes[0].values[-3]=2;nodes[0].values[7]=5;nodes[1].values[1]=99;
  nodes[0].labels["a"]=3;nodes[0].labels["z"]=4;
  fixed_nodes[0]=nodes[0];queue.push_back(nodes[0]);queue.push_back(nodes[1]);
  choice=0;calls=0;observed=0;
  foreach(nodes[pick()].values[k])begin
   choice=1;observed+=nodes[0].values[k];
  end
  if(calls!=3 || observed!=2)$fatal(1,"receiver must be evaluated for first and next");
  foreach(queue[0].labels[key])observed+=queue[0].labels[key];
  foreach(fixed_nodes[0].values[k])begin
   if(k<0)continue;
   observed+=fixed_nodes[0].values[k];
   break;
  end
  if(observed!=14)$fatal(1,"selected container iteration");
  $display("TRACE foreach selections observed=%0d calls=%0d",observed,calls);$finish;
 end
endmodule
