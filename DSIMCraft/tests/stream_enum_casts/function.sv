module top;
 typedef enum bit[3:0] {A=3,B=10} item_t;
 bit bits_value[];item_t value;
 function automatic item_t decode(input bit data[]);return item_t'({<<bit{data}});endfunction
 initial begin bits_value=new[4];bits_value[1]=1;bits_value[3]=1;value=decode(bits_value);if(value!=B)$fatal(1,"enum result");$display("TRACE stream enum function %0d %s",value,value.name());end
endmodule
