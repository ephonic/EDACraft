module top;
 typedef enum int {NEG=-2,POS=7} item_t;
 class holder;item_t value;endclass
 holder h;bit bits_value[];item_t observed;
 initial begin h=new();bits_value=new[32];foreach(bits_value[i])bits_value[i]=(i!=31);h.value=item_t'({>>{bits_value}});observed=h.value;if(observed!=NEG)$fatal(1,"signed enum");$display("TRACE stream enum property %0d %s",observed,observed.name());end
endmodule
