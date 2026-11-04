module unit_test #(parameter N=3)(output int total);
 class Store;
  int entries[int unsigned];
  function int visit();int result=0;foreach(this.entries[i])begin
    if(i<0)return -999;result+=entries[i];end
    return result;
  endfunction
 endclass
 Store s=new;
 initial begin
  int unsigned key;
  s.entries[-1]=N;s.entries[0]=N+1;s.entries[32'h80000000]=N+2;
  if(!s.entries.first(key)||key!=0||!s.entries.next(key)||key!=32'h80000000)$fatal(1,"class cursor");
  s.entries[-1][3:0]=5;
  total=s.visit();
  s.entries.delete(32'h80000000);
  if(s.entries.num()!=2||s.entries.exists(32'h80000000))$fatal(1,"class deletion");
 end
endmodule
module top;
 int x,y;unit_test #(3) a(x);unit_test #(7) b(y);int observed;
 initial begin #1;observed=x+y;if(x!=14||y!=22)$fatal(1,"class/instance isolation %d %d",x,y);
 $display("TRACE classes %0d",observed);$finish;end
endmodule
