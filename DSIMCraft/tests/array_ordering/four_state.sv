module top;
 logic [3:0] q[$],before_values[$];int counts[16],observed;bit found;
 initial begin
  q='{4'hx,4'h3,4'hz,4'h1,4'h7,4'b0x10};before_values=q;
  q.sort();if(q.size()!=before_values.size())$fatal(1,"unknown size");
  foreach(before_values[i])begin found=0;foreach(q[j])if(q[j]===before_values[i])found=1;if(!found)$fatal(1,"unknown permutation");end
  q.rsort();q.reverse();foreach(before_values[i])begin found=0;foreach(q[j])if(q[j]===before_values[i])found=1;if(!found)$fatal(1,"reverse permutation");end
  observed=q.size();$display("TRACE ordering four_state %0d",observed);$finish;
 end
endmodule
