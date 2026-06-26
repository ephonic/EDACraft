from gpgpu_stack import (
    DeviceContractBundle,
    build_gpu_sm_cluster_device_contract,
    build_gpu_sm_seed_device_contract,
)


def test_gpu_sm_seed_device_contract_bundles_shared_schemas():
    contract = build_gpu_sm_seed_device_contract()

    assert isinstance(contract, DeviceContractBundle)
    assert contract.name == "gpu_sm_seed"
    assert contract.address_map.region("cmdq").kind == "descriptor"
    assert contract.perf_counters.counter("issued_warps").category == "throughput"
    assert contract.supported_queues == ("compute",)
    assert contract.supported_opcodes == ("launch_kernel",)


def test_gpu_sm_cluster_device_contract_bundles_cluster_schemas():
    contract = build_gpu_sm_cluster_device_contract(sm_count=2)

    assert isinstance(contract, DeviceContractBundle)
    assert contract.name == "gpu_sm_cluster_seed"
    assert contract.address_map.region("cluster_csr").kind == "csr"
    assert contract.address_map.region("sm1_shared_mem_window").kind == "scratchpad"
    assert contract.perf_counters.counter("cluster_commit_commits").category == "throughput"
    assert contract.perf_counters.counter("sm0_shared_mem_stall_cycles").category == "stall"
    assert contract.metadata["sm_count"] == 2
