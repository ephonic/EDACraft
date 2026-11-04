`timescale 1ns/1ps
module t11;
    typedef enum logic [1:0] { IDLE = 0, RUN = 1 } st_e;
    st_e s = RUN;
    string nm;
    initial begin
        nm = s.name;
        if (nm == "RUN") $display("T11_ENUM_NAME PASS %s", nm);
        else $display("T11_ENUM_NAME FAIL nm=%s", nm);
        $finish;
    end
endmodule
