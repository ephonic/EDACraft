`timescale 1ns/1ps
module t08;
    typedef struct packed { logic [7:0] a; logic [7:0] d; logic w; } req_t;
    req_t r;
    function automatic logic [16:0] pack_req(req_t q);
        return {q.a, q.d, q.w};
    endfunction
    initial begin
        r.a = 8'hA5; r.d = 8'hFF; r.w = 1'b1;
        if (pack_req(r) === 17'h14BFF) $display("T08_STRUCT_ARG PASS");
        else $display("T08_STRUCT_ARG FAIL got=%h", pack_req(r));
        $finish;
    end
endmodule
