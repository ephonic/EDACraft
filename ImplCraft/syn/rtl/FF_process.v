`timescale 1ns/1ps
module FF_process (
    input wire [3:0]FF_opcode,
    input wire FF_Sel_1,FF_Sel_2,FF_Sel_3,FF_Sel_4,
    input wire [3:0]control,
    input wire Last_FF_Value,
    output reg FF_out
);

always @(*) begin
    case(FF_opcode)
        4'b0000:    begin                                
                        if (FF_Sel_2 == control[3]) 
                            FF_out = control[0];
                        else
                            FF_out = control[1];
                    end    
        4'b0001:    begin                                  
                        if (FF_Sel_2 == control[3]) 
                            FF_out = control[0];
                        else
                            FF_out = FF_Sel_3;
                    end
        4'b0010:    begin                                 
                        if (FF_Sel_2 == control[3]) 
                            FF_out = FF_Sel_1;
                        else
                            FF_out = FF_Sel_3;
                    end
        4'b0011:    begin                                
                        if (FF_Sel_2 == control[3]) 
                            FF_out = FF_Sel_1;
                        else
                            FF_out = control[1]; 
                    end   
        4'b0100:    FF_out = control[0];                 
        4'b0101:    FF_out = FF_Sel_1;                        
        4'b0110:    begin                                  
                        if (FF_Sel_2 == control[3]) 
                            FF_out = control[0];
                        else
                            FF_out = Last_FF_Value;
                    end
        4'b0111:    begin                                 
                        if (FF_Sel_2 == control[3]) 
                            FF_out = FF_Sel_1;
                        else
                            FF_out = Last_FF_Value;
                    end
        4'b1000:    begin                                  
                        if (FF_Sel_2 == control[3])     
                            FF_out = control[0];
                        else if (FF_Sel_4 == control[2])
                            FF_out = control[1];
                        else  
                            FF_out = Last_FF_Value;
                    end
        4'b1001:    begin                                  
                        if (FF_Sel_2 == control[3]) 
                            FF_out = control[0];
                        else if (FF_Sel_4 == control[2])
                            FF_out = FF_Sel_3;
                        else  
                            FF_out = Last_FF_Value;                            
                    end
        4'b1010:    begin                                                             
                        if (FF_Sel_2 == control[3]) 
                            FF_out = FF_Sel_1;
                        else if (FF_Sel_4 == control[2])
                            FF_out = control[1];
                        else  
                            FF_out = Last_FF_Value;                            
                    end
        4'b1011:    begin                                  
                        if (FF_Sel_2 == control[3]) 
                            FF_out = FF_Sel_1;
                        else if (FF_Sel_4 == control[2])
                            FF_out = FF_Sel_3;
                        else  
                            FF_out = Last_FF_Value;                            
                    end 
        4'b1100:    begin                                  
                        if (FF_Sel_2 == control[3])
                            begin
                                if (FF_Sel_4 == control[2])        
                                    FF_out = control[0];
                                else
                                    FF_out = control[1];                
                            end 
                        else
                            FF_out = Last_FF_Value;                        
                    end 
        4'b1101:    begin                                  
                        if (FF_Sel_2 == control[3])
                            begin
                                if (FF_Sel_4 == control[2])        
                                    FF_out = control[0];
                                else
                                    FF_out = FF_Sel_3;                
                            end 
                        else
                            FF_out = Last_FF_Value;                        
                    end     
        4'b1110:    begin                                  
                        if (FF_Sel_2 == control[3])
                            begin
                                if (FF_Sel_4 == control[2])        
                                    FF_out = FF_Sel_1;
                                else
                                    FF_out = control[1];                
                            end 
                        else
                            FF_out = Last_FF_Value;                        
                    end   
        4'b1111:    begin                                  
                        if (FF_Sel_2 == control[3])
                            begin
                                if (FF_Sel_4 == control[2])        
                                    FF_out = FF_Sel_1;
                                else
                                    FF_out = FF_Sel_3;                
                            end 
                        else
                            FF_out = Last_FF_Value;                        
                    end                                      
        default:    FF_out = Last_FF_Value;

    endcase
end

endmodule //FF_process
