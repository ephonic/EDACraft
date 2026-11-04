module top;
 typedef int count_t;
 class Counter;int value;function void advance();value++;endfunction endclass
 Counter counter=new;
 int observed,steps;
 function int bump();steps++;return steps;endfunction
 initial begin
  for(count_t i=0;steps<4;bump(),i++)begin
   if(i==1)continue;
   observed+=i;
  end
  if(observed!=5 || steps!=4)$fatal(1,"function step/continue");
  for(count_t i=0;counter.value<3;counter.advance(),i++)observed+=i;
  if(observed!=8 || counter.value!=3)$fatal(1,"void member step");
  $display("TRACE function step %0d %0d %0d",observed,steps,counter.value);
 end
endmodule
