module top;
 class Sample;
  rand bit[3:0] value;
  int limits[string][$];
  constraint bounds {foreach(limits[k,i])value>=limits[k][i]+i;value<10;}
 endclass
 Sample sample;int observed;
 initial begin
  sample=new;sample.limits["a"]='{2,6};sample.limits["b"]='{5};
  repeat(4)begin
   if(!sample.randomize()||sample.value<7||sample.value>=10)$fatal(1,"mixed constraints");
   observed++;
  end
  sample.limits.delete();sample.limits["a"]='{8};
  if(!sample.randomize()||sample.value<8||sample.value>=10)$fatal(1,"changed mixed constraints");
  observed++;$display("TRACE mixed constraints %0d",observed);$finish;
 end
endmodule
