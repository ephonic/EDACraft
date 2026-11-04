module tb;
    class Packet;
        int id;
        function new(int i); id = i; endfunction
        virtual function int get(); return id; endfunction
    endclass
    class ExtP extends Packet;
        int extra;
        function new(int i, int e); super.new(i); extra = e; endfunction
        virtual function int get(); return id + extra; endfunction
    endclass
    Packet p;
    ExtP e;
    initial begin
        p = new(5); e = new(6, 10);
        if (p.get() == 5 && e.get() == 16) $display("PROBE_CLASS: ok");
        else $display("PROBE_CLASS: BAD %0d %0d", p.get(), e.get());
        $finish;
    end
endmodule
