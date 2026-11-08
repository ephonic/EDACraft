set(TIME_ENGINE_SOURCES
src/liberty/liberty_binary.cc
    src/liberty/liberty_compress.cc
    src/parser/liberty_parser.cc

    src/graph/timing_graph.cc

    src/parasitics/elmore_calc.cc
    src/parser/spef_parser.cc
    src/parser/gate_netlist_parser.cc
    src/parser/verilog_parser_adapter.cc
    src/network/gate_view_adapter.cc

    src/dcalc/nldm_dcalc.cc
    src/dcalc/csm_dcalc.cc
    src/dcalc/rc_waveform_dcalc.cc
    src/dcalc/rc_surface_dcalc.cc
    src/dcalc/awe_dcalc.cc
    src/dcalc/unified_dcalc.cc
    src/dcalc/dmp_ceff.cc

    src/search/arrival_propagator.cc
    src/search/driving_cell.cc
    src/search/required_propagator.cc
    src/search/path_collector.cc

    src/sdc/core_sdc_applier.cc

    src/storage/mmap_store.cc

    src/incremental/dirty_tracker.cc

    src/engine/engine_impl.cc
    src/engine/scenario_manager.cc
    src/engine/si_waveform.cc
    src/engine/power_analysis.cc
    src/engine/api_c.cc
)
