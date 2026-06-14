// Auto-generated from SpecIR constraint RV32M_DIV_ZERO
class rv32m_div_zero_seq extends uvm_sequence #(rv32_transaction);
    `uvm_object_utils(rv32m_div_zero_seq)

    function new(string name = "rv32m_div_zero_seq");
        super.new(name);
    endfunction

    virtual task body();
        rv32_transaction req;
        // x1 = 7, x2 = 0; DIV x5, x1, x2 -> -1
        req = rv32_transaction::type_id::create("req");
        start_item(req);
        req.insn      = 32'h0220c2b3;
        req.rs1_val   = 32'h00000007;
        req.rs2_val   = 32'h00000000;
        finish_item(req);

        // REM x6, x1, x2 -> 7
        req = rv32_transaction::type_id::create("req");
        start_item(req);
        req.insn      = 32'h0220e333;
        req.rs1_val   = 32'h00000007;
        req.rs2_val   = 32'h00000000;
        finish_item(req);
    endtask
endclass
