module top;
 int source[5:1]='{5,3,5,2,3};
 int q[$],indices[$],empty[$];
 int aa[int];
 int observed;
 initial begin
  q=source.unique();if(q.size()!=3 || q.sum()!=10)$fatal(1,"unique elements");
  indices=source.unique_index();
  if(indices.size()!=3 || source[indices[0]]==source[indices[1]] || source[indices[0]]==source[indices[2]] || source[indices[1]]==source[indices[2]])$fatal(1,"unique indices");
  indices=source.find_index(x) with(x==3);
  if(indices.size()!=2 || indices[0]+indices[1]!=5 || indices[0]==indices[1])$fatal(1,"descending fixed indices");
  q=source.find_first with(item>2);if(q.size()!=1 || q[0]!=5)$fatal(1,"find first");
  indices=source.find_last_index with(item>2);if(indices.size()!=1 || indices[0]!=1)$fatal(1,"find last index");
  q=source.find with(item<4);if(q.size()!=3 || q.sum()!=8)$fatal(1,"find values");
  q=source.min();if(q.size()!=1 || q[0]!=2)$fatal(1,"minimum");
  q=source.max();if(q.size()!=1 || q[0]!=5)$fatal(1,"maximum");
  q=source.min with(-item);if(q.size()!=1 || q[0]!=5)$fatal(1,"signed key");
  q={3,2,3,1};q=q.unique;if(q.size()!=3 || q.sum()!=6)$fatal(1,"self assignment snapshot");
  q=empty.unique();if(q.size()!=0)$fatal(1,"empty unique");
  q=empty.min();if(q.size()!=0)$fatal(1,"empty minimum");
  aa[-7]=4;aa[2]=6;aa[20]=4;
  q=aa.unique;if(q.size()!=2 || q.sum()!=10)$fatal(1,"associative values");
  indices=aa.find_index with(item==4);
  if(indices.size()!=2 || indices[0]+indices[1]!=13 || indices[0]==indices[1])$fatal(1,"associative indices");
  q=source.unique;observed=q.size();if(observed!=3)$fatal(1,"computed queue size");
  #1;$display("TRACE locators values count=%0d",observed);$finish;
 end
endmodule
