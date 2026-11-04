typedef enum logic[3:0]{LOW=2,HIGH=10} mode_t;
typedef logic[95:0] wide_t;
interface bus_if;
 function automatic mode_t mode();return HIGH;endfunction
 function automatic wide_t wide();return 96'hfedcba987654321001234567;endfunction
 function automatic real fraction();return 1.25;endfunction
endinterface
module top;
 bus_if a();virtual bus_if vif;mode_t value;wide_t bits_value;real r;
 initial begin vif=a;value=vif.mode();bits_value=vif.wide();r=vif.fraction();
  if(value!=HIGH||bits_value!==96'hfedcba987654321001234567||r!=1.25)$fatal(1,"return metadata");
  $display("TRACE vif types %s %h %0.2f",value.name(),bits_value,r);
 end
endmodule
