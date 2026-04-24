// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : sha3_driver.sv
// Module Name : SHA3Driver
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef SHA3DRIVER_SV
`define SHA3DRIVER_SV

import sha3_256_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class SHA3Driver extends uvm_driver #(SHA3Txn);
    `uvm_component_utils(SHA3Driver)

    virtual task run_phase(uvm_phase phase);
        SHA3Txn req;
        forever begin
            this.seq_item_port.get_next_item(req);
            while ((!this.vif.cb.i_ready)) begin
                @vif.cb;
            end
            this.vif.cb.i_valid <= 1;
            this.vif.cb.block <= req.block;
            this.vif.cb.block_len <= req.msg_len;
            this.vif.cb.last_block <= 1;
            @vif.cb;
            this.vif.cb.i_valid <= 0;
            this.vif.cb.last_block <= 0;
            this.seq_item_port.item_done();
        end
    endtask

endclass : SHA3Driver

`endif // SHA3DRIVER_SV
