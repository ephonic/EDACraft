from gpgpu_stack import AddressMap, PerfCounterSchema
from gpgpu_stack.contracts import (
    build_gpu_sm_cluster_address_map,
    build_gpu_sm_cluster_perf_counter_schema,
    build_gpu_sm_seed_address_map,
    build_gpu_sm_seed_perf_counter_schema,
)


def test_gpu_sm_seed_address_map_is_stable_and_non_overlapping():
    addr_map = build_gpu_sm_seed_address_map()

    assert isinstance(addr_map, AddressMap)
    assert addr_map.name == "gpu_sm_seed_addr_map"
    assert addr_map.region("csr").base == 0x0000_0000
    assert addr_map.region("cmdq").kind == "descriptor"
    assert addr_map.find_region(0x0002_0008).name == "perf_counters"
    assert addr_map.find_region(0xFFFF_FFFF) is None


def test_gpu_sm_seed_perf_counter_schema_is_stable():
    schema = build_gpu_sm_seed_perf_counter_schema()

    assert isinstance(schema, PerfCounterSchema)
    assert schema.schema_id == "gpu_sm_seed_perf"
    assert schema.counter("issued_warps").category == "throughput"
    assert schema.counter("shared_mem_stall_cycles").category == "stall"
    assert schema.counter("sfu_busy_cycles").width_bits == 64


def test_gpu_sm_cluster_address_map_is_stable_and_non_overlapping():
    addr_map = build_gpu_sm_cluster_address_map(sm_count=2)

    assert isinstance(addr_map, AddressMap)
    assert addr_map.name == "gpu_sm_cluster_seed_addr_map"
    assert addr_map.region("cluster_csr").base == 0x0000_0000
    assert addr_map.region("sm0_shared_mem_window").kind == "scratchpad"
    assert addr_map.region("sm1_shared_mem_window").base == 0x0010_4000
    assert addr_map.find_region(0x0002_0008).name == "perf_counters"
    assert addr_map.find_region(0x0010_4010).name == "sm1_shared_mem_window"


def test_gpu_sm_cluster_perf_counter_schema_is_stable():
    schema = build_gpu_sm_cluster_perf_counter_schema(sm_count=2)

    assert isinstance(schema, PerfCounterSchema)
    assert schema.schema_id == "gpu_sm_cluster_seed_perf"
    assert schema.counter("cluster_commit_commits").category == "throughput"
    assert schema.counter("cluster_mem_stall_cycles").category == "stall"
    assert schema.counter("sm0_sfu_busy_cycles").width_bits == 64
    assert schema.counter("sm1_writeback_commits").category == "throughput"
