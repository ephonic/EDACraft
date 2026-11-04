module top;
 typedef logic [15:0] Q[$:2];Q a[int];int observed;logic[15:0] v;
 initial begin
  a[-2].push_back(8);a[-2].push_front(3);a[-2].insert(1,5);a[-2].push_back(99);
  if(a.num()!=1||a[-2].size()!=3||a[-2][0]!=3||a[-2][1]!=5||a[-2][2]!=8)$fatal(1,"bounded methods");
  a[-2][1][7:0]=8'h12;a[-2][0]+=2;if(a[-2][1]!=18||a[-2][0]!=5)$fatal(1,"selected writes");
  v=a[-2].pop_front();if(v!=5)$fatal(1,"pop front");a[-2].delete(0);v=a[-2].pop_back();if(v!=8||a[-2].size()!=0||!a.exists(-2))$fatal(1,"delete index");
  a[4]='{1,2,3,4};if(a[4].size()!=3||a[4][2]!=3)$fatal(1,"bounded assignment");
  a[4].reverse();a[4].sort();a[4].rsort();if(a[4][0]!=3)$fatal(1,"bounded ordering");
  observed=a[4][0]+a.num();$display("TRACE mixed methods %0d",observed);$finish;
 end
endmodule
