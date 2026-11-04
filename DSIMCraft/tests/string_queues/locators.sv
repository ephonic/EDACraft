module top;
 string q[$],found[$],least[$],largest[$],distinct[$];int ids[$],observed;
 initial begin
  q='{"beta","alpha","beta","gamma"};
  found=q.find() with(item.len()==5);ids=q.find_index() with(item=="beta");
  least=q.min();largest=q.max();distinct=q.unique();
  if(found.size()!=2||found[0]!="alpha"||found[1]!="gamma"||ids.size()!=2||ids[0]!=0||ids[1]!=2)$fatal(1,"find string");
  if(least[0]!="alpha"||largest[0]!="gamma"||distinct.size()!=3)$fatal(1,"string comparison");
  observed=q.sum() with(item.len());if(observed!=18)$fatal(1,"mapped reduction");
  $display("TRACE locators %s %s %0d",least[0],largest[0],observed);$finish;
 end
endmodule
