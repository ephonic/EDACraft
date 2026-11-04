module top;
 int fixed_values[4:1],dynamic_values[],q[$],empty[$];
 real fractions[3];int observed;
 initial begin
  fixed_values='{8,-2,5,-7};fixed_values.sort;
  if(fixed_values[4]!=-7||fixed_values[3]!=-2||fixed_values[2]!=5||fixed_values[1]!=8)$fatal(1,"descending declaration order");
  fixed_values.rsort();if(fixed_values[4]!=8||fixed_values[1]!=-7)$fatal(1,"rsort");
  fixed_values.reverse;if(fixed_values[4]!=-7||fixed_values[1]!=8)$fatal(1,"reverse");
  dynamic_values=new[4];dynamic_values='{4,-3,0,12};dynamic_values.sort();
  if(dynamic_values[0]!=-3||dynamic_values[3]!=12)$fatal(1,"dynamic");
  dynamic_values.rsort;dynamic_values.reverse();if(dynamic_values[0]!=-3)$fatal(1,"dynamic reverse");
  q='{5,1,8,3};q.sort(value) with(-value);if(q[0]!=8||q[3]!=1)$fatal(1,"custom iterator");
  q.rsort with(-item);if(q[0]!=1||q[3]!=8)$fatal(1,"reverse key");
  empty.sort();empty.rsort;empty.reverse;empty.push_back(7);empty.sort with(-item);
  if(empty.size()!=1||empty[0]!=7)$fatal(1,"empty or singleton");
  fractions='{1.25,-3.5,0.125};fractions.sort();if(fractions[0]!=-3.5||fractions[2]!=1.25)$fatal(1,"real");
  fractions.rsort with(-item);if(fractions[0]!=-3.5)$fatal(1,"real key");
  observed=q[3]+fixed_values[1];$display("TRACE ordering numeric %0d",observed);$finish;
 end
endmodule
