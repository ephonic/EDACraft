from pathlib import Path

from gpgpu_stack import (
    AddressMap,
    AddressRegion,
    CommandDescriptor,
    KernelLaunch,
    KernelMetadata,
    PerfCounterSchema,
    PerfCounterSpec,
    WorkloadTrace,
    WorkloadTraceEvent,
    workload_trace_to_archsim_workload,
)


def test_workload_trace_bridges_to_archsim_workload():
    kernel = KernelMetadata(
        kernel_name="vec_add",
        grid_dim=(8, 1, 1),
        block_dim=(64, 1, 1),
        shared_mem_bytes=1024,
        register_count=32,
    )
    trace = WorkloadTrace(
        kernel=kernel,
        trace_id="vec_add_trace",
        events=(
            WorkloadTraceEvent(
                flow_name="warp_compute",
                path=("dispatch", "simd_alu", "writeback"),
                tokens=32,
            ),
            WorkloadTraceEvent(
                flow_name="warp_memory",
                path=("dispatch", "shared_mem", "writeback"),
                tokens=16,
                bytes_per_token=64,
                start_cycle=1,
            ),
        ),
    )

    workload = workload_trace_to_archsim_workload(trace)

    assert tuple(flow.name for flow in workload.flows) == ("warp_compute", "warp_memory")
    assert workload.flows[1].bytes_per_token == 64
    assert workload.flows[1].start_cycle == 1


def test_workload_trace_json_round_trip(tmp_path: Path):
    trace = WorkloadTrace(
        kernel=KernelMetadata(kernel_name="sfu_kernel"),
        trace_id="trace_json",
        metadata={"source": "compiler_stub"},
        events=(
            WorkloadTraceEvent(
                flow_name="warp_sfu",
                path=("dispatch", "sfu_pipe", "writeback"),
                tokens=8,
                bytes_per_token=16,
                metadata={"opclass": "sfu"},
            ),
        ),
    )

    path = trace.to_json_file(tmp_path / "trace.json")
    loaded = WorkloadTrace.from_json_file(path)

    assert loaded.trace_id == "trace_json"
    assert loaded.kernel.kernel_name == "sfu_kernel"
    assert loaded.events[0].flow_name == "warp_sfu"
    assert loaded.events[0].metadata["opclass"] == "sfu"


def test_command_descriptor_round_trip_dict():
    descriptor = CommandDescriptor(
        opcode="launch_kernel",
        queue="compute",
        priority=2,
        launch=KernelLaunch(
            metadata=KernelMetadata(kernel_name="gemm"),
            launch_id="launch0",
            args={"a_addr": 4096, "b_addr": 8192, "c_addr": 12288},
        ),
        metadata={"stream": 0},
    )

    restored = CommandDescriptor.from_dict(descriptor.to_dict())

    assert restored.opcode == "launch_kernel"
    assert restored.launch.launch_id == "launch0"
    assert restored.launch.args["b_addr"] == 8192
    assert restored.metadata["stream"] == 0


def test_address_map_round_trip_and_lookup():
    addr_map = AddressMap(
        name="demo_map",
        regions=(
            AddressRegion("csr", base=0x0, size_bytes=0x1000, kind="csr"),
            AddressRegion("scratch", base=0x1000, size_bytes=0x2000, kind="scratchpad"),
        ),
    )

    restored = AddressMap.from_dict(addr_map.to_dict())

    assert restored.region("csr").kind == "csr"
    assert restored.find_region(0x1800).name == "scratch"
    assert restored.find_region(0x4000) is None


def test_perf_counter_schema_round_trip():
    schema = PerfCounterSchema(
        schema_id="perf_demo",
        counters=(
            PerfCounterSpec("issued", category="throughput"),
            PerfCounterSpec("stall", category="stall", description="stall cycles"),
        ),
    )

    restored = PerfCounterSchema.from_dict(schema.to_dict())

    assert restored.counter("issued").category == "throughput"
    assert restored.counter("stall").description == "stall cycles"
