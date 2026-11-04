module top;
 class Key;int id;function new(int n);id=n;endfunction endclass
 class Sample;
  rand bit [3:0] value;
  int limits[Key];
  constraint bounds {foreach(limits[k])value>=k.id+limits[k];value<10;}
 endclass
 Sample sample;Key a,b;int observed;
 initial begin
  sample=new;a=new(1);b=new(3);sample.limits[a]=2;sample.limits[b]=4;
  repeat(8)begin
   if(!sample.randomize())$fatal(1,"object key constraints unsatisfied");
   if(sample.value<7||sample.value>=10)$fatal(1,"key member or value dropped");
   observed++;
  end
  sample.limits.delete(b);sample.limits[a]=6;
  if(!sample.randomize()||sample.value<7)$fatal(1,"current key map constraints");
  observed++;$display("TRACE constraint foreach typed object keys pass");
 end
endmodule
