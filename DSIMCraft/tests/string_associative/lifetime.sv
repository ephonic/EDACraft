module top;
 int one,two;
 task automatic work(input int tag);
   int map[string];string key;int sum;
   map["v"]=tag;#1;map["w"]=tag+1;
   foreach(map[k])begin #1;sum=sum+map[k]+k.len();end
   if(tag==3)one=sum;else two=sum;
 endtask
 function automatic int calculate(input int tag);
   int map[string];int sum;
   map[""]=tag;map["x"]=tag+1;
   foreach(map[k])sum=sum+map[k]+k.len();
   return sum;
 endfunction
 initial begin
   fork work(3);work(7);join
   $display("TRACE lifetime %0d %0d %0d %0d",one,two,calculate(4),calculate(8));
   #1;$finish;
 end
endmodule
