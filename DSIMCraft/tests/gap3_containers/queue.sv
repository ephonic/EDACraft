module top;
 typedef struct packed {logic [7:0] x;logic [7:0] y;} Pair;
 int q[$:4]='{1,2,3};int r[$]='{0,1};int empty[$];Pair pairs[$];int observed;
 function automatic int last(input int v[$]);return v[$];endfunction
 function automatic int before_last(input int v[$]);return v[($-1)];endfunction
 initial begin
  if(q[$]!=3||q[$-1]!=2||q[($-2)]!=1||q[r[$]]!=2||last(q)!=3||before_last(q)!=2)$fatal(1,"queue reads and nested context");
  q[$]=8;q[$-1]+=3;
  if(q[2]!=8||q[1]!=5)$fatal(1,"queue writes");
  q[$+1]=9;if(q.size()!=4||q[$]!=9)$fatal(1,"append");
  q[$+2]=99;if(q.size()!=4)$fatal(1,"non adjacent write");
  pairs.push_back(16'h1234);pairs[$].x=8'h56;pairs[$][3:0]=4'ha;
  if(pairs[0]!=16'h563a)$fatal(1,"packed queue field/slice");
  q.pop_back();if(q[$]!=8)$fatal(1,"size reevaluation");
  observed=q[$]+q[$-1];q.delete();
  if(q[$]!==0)$fatal(1,"empty int queue default");
  q[$]=7;if(q.size()!=0)$fatal(1,"empty invalid write");q[$+1]=4;
  if(q.size()!=1||q[$]!=4)$fatal(1,"empty append");
  q={};empty={};q={empty,5,empty};if(q.size()!=1||q[$]!=5)$fatal(1,"typed empty queue concatenation");
  #1;$display("TRACE queue %0d %0h",observed,pairs[$]);$finish;
 end
endmodule
