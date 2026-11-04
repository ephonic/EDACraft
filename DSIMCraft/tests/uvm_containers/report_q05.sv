module tb;
    int q[$];
    int da[];
    int aa[int];
    initial begin
        q.push_back(1); q.push_back(2); q.push_front(0);
        da = new[3];
        aa[5] = 50; aa[10] = 100;
        if (q.size() == 3 && q[0] == 0 && q[2] == 2 && da.size() == 3 && aa[5] == 50 && aa[10] == 100
            && aa.exists(5))
            $display("PROBE_ADTS: ok");
        else
            $display("PROBE_ADTS: BAD qsz=%0d", q.size());
        $finish;
    end
endmodule
