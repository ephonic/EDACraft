module top;
 typedef enum bit [27:0] {FIRST=1,SECOND=3} key_t;
 typedef bit [63:0] wide_t;
 class Sample;
  rand bit [3:0] value;
  int limits[key_t];int wide[wide_t];
  constraint bounds {foreach(limits[k])value>=int'(k)+limits[k];foreach(wide[w])value>=wide[w]+int'(w>>32);value<10;}
 endclass
 Sample sample;int observed;
 initial begin
  observed=0;sample=new;sample.limits[FIRST]=2;sample.limits[SECOND]=4;
  sample.wide[64'h100000000]=6;
  repeat(6)begin
   if(!sample.randomize()||sample.value<7||sample.value>=10)$fatal(1,"typed key constraint");
   observed++;
  end
  sample.wide[64'h200000000]=8;
  if(sample.randomize())$fatal(1,"upper limb lost in constraint index");
  sample.wide.delete(64'h200000000);
  if(!sample.randomize())$fatal(1,"current associative storage");
  observed++;if(observed!=7)$fatal(1,"constraint execution count");
  $display("TRACE typed key constraints pass");
 end
endmodule
