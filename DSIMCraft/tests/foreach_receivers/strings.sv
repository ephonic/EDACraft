module top;
 class Map;
  int entries[string];
  function int total();
   int sum=0;
   foreach(this.entries[key])sum+=this.entries[key];
   return sum;
  endfunction
  task automatic sample(output int result);
   result=0;
   foreach(this.entries[key])begin
    #1;result+=this.entries[key];
   end
  endtask
 endclass
 Map c;
 int observed;
 initial begin
  c=new;c.entries["a"]=2;c.entries["z"]=5;
  c.sample(observed);if(observed!=7 || c.total()!=7)$fatal(1,"string cursor receiver");
  $display("TRACE foreach receivers strings=%0d",observed);$finish;
 end
endmodule
