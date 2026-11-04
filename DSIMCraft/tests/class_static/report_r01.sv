module tb;
    class Base;
        int id;
        static int count = 0;
        function new(int i); id = i; count++; endfunction
        virtual function string name(); return "base"; endfunction
    endclass
    class Sub extends Base;
        int v;
        function new(int i, int x); super.new(i); v = x; endfunction
        virtual function string name(); return "sub"; endfunction
        function int total(); return id + v; endfunction
    endclass
    Base tab[3];
    Base b;
    Sub s;
    initial begin
        s = new(10, 32);
        b = s;                          // upcast: polymorphism
        tab[0] = new(1); tab[1] = s; tab[2] = null;
        if (b.name() == "sub" && tab[1].name() == "sub" && s.total() == 42
            && Base::count == 2 && (tab[2] == null))
            $display("PROBE_CLASS2: ok (poly/static/null/scope-resolve)");
        else
            $display("PROBE_CLASS2: BAD %s %0d cnt=%0d", b.name(), s.total(), Base::count);
        $finish;
    end
endmodule
