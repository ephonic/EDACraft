typedef logic [64:0] data_t;
class Item;
 data_t value[];
 function void get_value_array(ref data_t result[]);result=value;endfunction
 function void set_value_array(const ref data_t source[]);value=source;endfunction
 function void copy(input Item rhs);rhs.get_value_array(value);endfunction
endclass
module top;
 Item first,second;int stage=0;
 initial begin
  first=new();second=new();first.value=new[2];first.value[0]=65'h10000000000000001;first.value[1]=65'h10000000000000002;
  second.copy(first);$display("TRACE copy %0d %h %h",second.value.size(),second.value[0],second.value[1]);
  first.value[0]=65'h10000000000000003;stage++;#1;
  $display("TRACE independent %h %h",first.value[0],second.value[0]);
  first.set_value_array(second.value);$display("TRACE const %h",first.value[0]);$finish;
 end
endmodule
