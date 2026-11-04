module top;
 typedef enum logic[3:0] {A=3,B=10} item_t;
 bit bits_value[];item_t value;
 initial begin bits_value=new[4];bits_value[2]=1;bits_value[3]=1;value=item_t'({>>{bits_value}});if(value!=A)$fatal(1,"enum identity");$display("TRACE stream enum %0d %s",value,value.name());end
endmodule
