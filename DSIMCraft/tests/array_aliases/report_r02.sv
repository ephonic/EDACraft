module tb;
    int q[$];
    int aa[string];
    int da[];
    int k, v;
    string s;
    initial begin
        q = {1, 2, 3};
        q.insert(1, 9);                 // 1 9 2 3
        q.delete(0);                    // 9 2 3
        da = new[4]; da[0]=10; da[3]=40;
        da = new[6](da);                // grow preserving
        aa["x"] = 5; aa["y"] = 7;
        if (q.size() == 3 && q[0] == 9 && q[1] == 2
            && da.size() == 6 && da[3] == 40
            && aa.num() == 2 && aa.first(s) && aa[s] == 5 && s == "x"
            && aa.next(s) && s == "y")
            $display("PROBE_ADT2: ok (insert/delete/new[n](old)/num/first/next/string keys)");
        else
            $display("PROBE_ADT2: BAD qsz=%0d da=%0d aan=%0d", q.size(), da.size(), aa.num());
        $finish;
    end
endmodule
