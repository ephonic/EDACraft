module tb;
    integer hits = 0;
    function void bg_start();
        fork begin #0; hits = hits + 1; end join_none   // zero-time-only child in function
    endfunction
    initial begin
        bg_start();
        #5;
        if (hits == 1) $display("FORKFN: ok");
        else $display("FORKFN: BAD hits=%0d", hits);
        $finish;
    end
endmodule
