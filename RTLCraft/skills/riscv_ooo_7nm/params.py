"""7nm out-of-order RISC-V core parameter specification."""

from rtlgen.params import ConfigSpec


OOO_7NM_PARAMS = {
    "isa": "riscv64",
    "xlen": 64,
    "m_extension": True,
    "a_extension": True,
    "c_extension": True,
    "f_extension": True,
    "d_extension": True,
    "fetch_width": 8,
    "decode_width": 6,
    "rename_width": 6,
    "dispatch_width": 6,
    "commit_width": 6,
    "rob_size": 256,
    "nr_phy_regs": 192,
    "nr_arch_regs": 32,
    "issue_queue_size": 16,
    "alu_pipes": 4,
    "mul_pipe": True,
    "div_pipe": True,
    "fpu_pipes": 4,
    "load_pipes": 2,
    "store_pipes": 2,
    "lq_size": 80,
    "sq_size": 64,
    "ibuf_size": 48,
    "btb_entries": 1024,
    "bht_entries": 4096,
    "ras_depth": 16,
    "tage_tables": 6,
    "icache_size": 32768,
    "icache_ways": 8,
    "dcache_size": 32768,
    "dcache_ways": 8,
    "dcache_line_size": 64,
    "l2_size": 262144,
    "l2_ways": 8,
    "tlb_entries": 64,
    "l2_tlb_entries": 512,
    "tech_node": "7nm",
    "target_freq_mhz": 2000,
    "core_name": "riscv_ooo_7nm",
}


def ooo_7nm_params() -> ConfigSpec:
    """Return the 7nm OoO core parameter specification."""
    return ConfigSpec(_values=dict(OOO_7NM_PARAMS))
