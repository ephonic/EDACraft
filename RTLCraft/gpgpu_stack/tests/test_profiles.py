from gpgpu_stack import get_gpu_sm_named_profile


def test_named_gpu_sm_profiles_cover_distinct_pressure_shapes():
    baseline = get_gpu_sm_named_profile("baseline")
    memory = get_gpu_sm_named_profile("memory_pressure")
    compute = get_gpu_sm_named_profile("compute_pressure")
    sfu = get_gpu_sm_named_profile("sfu_pressure")

    assert memory.memory_tokens > baseline.memory_tokens
    assert memory.memory_bytes_per_token > baseline.memory_bytes_per_token
    assert compute.compute_tokens > baseline.compute_tokens
    assert compute.gemm_tokens > baseline.gemm_tokens
    assert sfu.sfu_tokens > baseline.sfu_tokens
    assert sfu.sfu_bytes_per_token > baseline.sfu_bytes_per_token
