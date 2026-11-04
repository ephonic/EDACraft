#!/usr/bin/env python3
"""Build and smoke-test an immutable local release, then atomically update bin/dsim."""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parents[1]
HEADERS = ("constraint", "dpi", "runtime", "waveform", "path", "path_dictionary", "wide_value", "parallel", "partition", "parallel_waveform")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def publish(prefix, build, check_groups=None, stage_only=False, check_jobs=1, command_timeout=900):
    prefix = prefix.expanduser().resolve()
    build = build.expanduser().resolve()
    # Compiler and parser inputs, excluding generated validation artifacts.
    inputs = sorted({ROOT / "CMakeLists.txt", Path(__file__),ROOT / "scripts/compile_split_model.py",
                     *ROOT.joinpath("tests/ipc").rglob("*"),
                     *ROOT.joinpath("tests/process_handles").rglob("*"),
                     *ROOT.joinpath("tests/process_lifetime").rglob("*"),
                     *ROOT.joinpath("tests/shared_tasks").rglob("*"),
                     *ROOT.joinpath("tests/array_streams").rglob("*"),
                     *ROOT.joinpath("tests/associative_values").rglob("*"),
                     *ROOT.joinpath("tests/object_scalar_refs").rglob("*"),
                     *ROOT.joinpath("tests/stream_targets").rglob("*"),
                     *ROOT.joinpath("tests/stream_enum_casts").rglob("*"),
                     *ROOT.joinpath("tests/virtual_interfaces").rglob("*"),
                     *ROOT.joinpath("tests/virtual_interface_calls").rglob("*"),
                     *ROOT.joinpath("tests/uvm_preprocess").glob("*.sv"),
                     *ROOT.joinpath("tests/typed_for").rglob("*"),
                     *ROOT.joinpath("tests/gap3_containers").rglob("*"),
                     *ROOT.joinpath("tests/time_literals").rglob("*"),
                     ROOT / "tests/typed_execution.py",
                     *ROOT.joinpath("tests/anonymous_enums").rglob("*"),
                     *ROOT.joinpath("tests/enums").rglob("*"),
                     *ROOT.joinpath("tests/runtime_array_patterns").rglob("*"),
                     *ROOT.joinpath("tests/const_variables").rglob("*"),
                     *ROOT.joinpath("tests/constraint_randomization").rglob("*"),
                     *ROOT.joinpath("tests/compilation_types").rglob("*"),
                     *ROOT.joinpath("tests/constraint_foreach").rglob("*"),
                     *ROOT.joinpath("tests/foreach_receivers").rglob("*"),
                     *ROOT.joinpath("tests/foreach_selections").rglob("*"),
                     *ROOT.joinpath("tests/const_properties").rglob("*"),
                     *ROOT.joinpath("tests/nonansi_bodies").rglob("*"),
                     *ROOT.joinpath("tests/array_locators").rglob("*"),
                     *ROOT.joinpath("tests/string_casts").rglob("*"),
                     *ROOT.joinpath("tests/real_values").rglob("*"),
                     *ROOT.joinpath("tests/time").rglob("*"),
                     *ROOT.joinpath("tests/dpi").rglob("*"),
                     *ROOT.joinpath("tests/chandle").rglob("*"),
                     *ROOT.joinpath("tests/struct_strings").rglob("*"),
                     *ROOT.joinpath("tests/extern_methods").rglob("*"),
                     *ROOT.joinpath("tests/class_parameter_lists").rglob("*"),
                     *ROOT.joinpath("tests/parameterized_formals").rglob("*"),
                     *ROOT.joinpath("tests/dynamic_initializers").glob("*.sv"),
                     ROOT / "tests/dynamic_initializers/expected.json",
                     *ROOT.joinpath("tests/array_state_conversion").rglob("*.sv"),
                     *ROOT.joinpath("tests/array_state_conversion").rglob("expected.json"),
                     *ROOT.joinpath("tests/fixed_initializers").glob("*.sv"),
                     ROOT / "tests/fixed_initializers/expected.json",
                     *ROOT.joinpath("tests/frontend_compat").rglob("*"),
                     *ROOT.joinpath("tests/instance_arrays").rglob("*"),
                     *ROOT.joinpath("tests/assignment_patterns").rglob("*"),
                     *ROOT.joinpath("tests/streaming").rglob("*"),
                     *ROOT.joinpath("tests/array_reductions").rglob("*"),
                     *ROOT.joinpath("tests/reduction_with").rglob("*"),
                     *ROOT.joinpath("tests/reported_cases").rglob("*"),
                     *ROOT.joinpath("tests/rtl_report").rglob("*"),
                     *ROOT.joinpath("tests/random_functions").rglob("*"),
                     *ROOT.joinpath("tests/packages").rglob("*"),
                     *ROOT.joinpath("tests/package_lifetimes").rglob("*"),
                     *ROOT.joinpath("tests/compilation_imports").rglob("*"),
                     *ROOT.joinpath("tests/uvm_containers").rglob("*"),
                     *ROOT.joinpath("tests/class_objects").rglob("*"),
                     *ROOT.joinpath("tests/class_inheritance").rglob("*"),
                     *ROOT.joinpath("tests/class_casts").rglob("*"),
                     *ROOT.joinpath("tests/class_forward").rglob("*"),
                     *ROOT.joinpath("tests/typed_containers").rglob("*"),
                     *ROOT.joinpath("tests/string_queues").rglob("*"),
                     *ROOT.joinpath("tests/coverage").rglob("*"),
                     *ROOT.joinpath("tests/integral_folding").rglob("*"),
                     *ROOT.joinpath("tests/array_ordering").rglob("*"),
                     *ROOT.joinpath("tests/mixed_queues").rglob("*"),
                     *ROOT.joinpath("tests/struct_containers").rglob("*"),
                     *ROOT.joinpath("tests/struct_associative").rglob("*"),
                     *ROOT.joinpath("tests/class_events").rglob("*"),
                     *ROOT.joinpath("tests/class_associative_strings").rglob("*"),
                     *ROOT.joinpath("tests/class_dynamic_arrays").rglob("*"),
                     *ROOT.joinpath("tests/class_handle_arrays").rglob("*"),
                     *ROOT.joinpath("tests/recursive_functions").rglob("*"),
                     *ROOT.joinpath("tests/class_body_parameters").rglob("*"),
                     *ROOT.joinpath("tests/integral_keys").rglob("*"),
                     *ROOT.joinpath("tests/multidim_associative").rglob("*"),
                     *ROOT.joinpath("tests/string_associative").rglob("*"),
                     *ROOT.joinpath("tests/class_access").rglob("*"),
                     *ROOT.joinpath("tests/class_static").rglob("*"),
                     *ROOT.joinpath("tests/subroutine_labels").rglob("*"),
                     *ROOT.joinpath("tests/array_aliases").rglob("*"),
                     *ROOT.joinpath("tests/parameterized_classes").rglob("*"),
                     *ROOT.joinpath("tests/waveform_pipeline").rglob("*"),
                     *ROOT.joinpath("tests/waveform_selection").rglob("*"),
                     ROOT / "scripts/run_flow.py",
                     *ROOT.joinpath("tests/unit_lifetimes").rglob("*"),
                     *ROOT.joinpath("tests/header_imports").rglob("*"),
                     *ROOT.joinpath("tests/package_exports").rglob("*"),
                     *ROOT.joinpath("tests/budget_resume").rglob("*"),
                     *ROOT.joinpath("tests/strings").rglob("*"),
                     *ROOT.joinpath("tests/liberty_db").rglob("*"),
                     *ROOT.joinpath("tests/string_subroutines").rglob("*"),
                     *ROOT.joinpath("tests/concurrent_assertions").rglob("*"),
                     *ROOT.joinpath("tests/clocking").rglob("*"),
                     *ROOT.joinpath("tests/sequence_delays").rglob("*"),
                     *ROOT.joinpath("tests/sequence_repetition").rglob("*"),
                     *ROOT.joinpath("tests/sequence_groups").rglob("*"),
                     *ROOT.joinpath("tests/named_sequences").rglob("*"),
                     *ROOT.joinpath("tests/sequence_antecedents").rglob("*"),
                     *ROOT.joinpath("tests/memory_cases").rglob("*"),
                     *ROOT.joinpath("tests/comb_partial").rglob("*"),
                     *ROOT.joinpath("tests/comb_sensitivity").rglob("*"),
                     *ROOT.joinpath("tests/ascending_packed").rglob("*"),
                     *ROOT.joinpath("tests/named_types").rglob("*"),
                     *ROOT.joinpath("tests/packed_aggregates").rglob("*"),
                     *ROOT.joinpath("tests/unpacked_state").rglob("*"),
                     *ROOT.joinpath("tests/report3").rglob("*"),
                     *ROOT.joinpath("tests/report4").rglob("*"),
                     *ROOT.joinpath("tests/report5").rglob("*"),
                     *ROOT.joinpath("tests/report6").rglob("*"),
                     *ROOT.joinpath("tests/integral_loops").rglob("*"),
                     *ROOT.joinpath("tests/wait_rearm").rglob("*"),
                     *ROOT.joinpath("tests/compiled_wait").rglob("*"),
                     *ROOT.joinpath("tests/static_net_drives").rglob("*"),
                     *ROOT.joinpath("tests/scalar_edges").rglob("*"),
                     *ROOT.joinpath("tests/comb_regions").rglob("*"),
                     *ROOT.joinpath("tests/wake_dispatch").rglob("*"),
                     *ROOT.joinpath("tests/comb_leaves").rglob("*"),
                     *ROOT.joinpath("tests/typed_stores").rglob("*"),
                     *ROOT.joinpath("tests/selection_flush").rglob("*"),
                     *ROOT.joinpath("tests/selection_checks").rglob("*"),
                     *ROOT.joinpath("tests/hierarchical_arrays").rglob("*"),
                     *ROOT.joinpath("tests/c910_frontend").rglob("*"),
                     *ROOT.joinpath("tests/compact_memories").rglob("*"),
                     *ROOT.joinpath("tests/uvm_call_values").rglob("*"),
                     *ROOT.joinpath("tests/type_reflection").rglob("*"),
                     *ROOT.joinpath("tests/array_equality").rglob("*"),
                     *ROOT.joinpath("tests/queue_slices").rglob("*"),
                     *ROOT.joinpath("tests/late_class_binding").rglob("*"),
                     *ROOT.joinpath("tests/swrite").rglob("*"),
                     *ROOT.joinpath("tests/object_format").rglob("*"),
                     *ROOT.joinpath("tests/callback_types").rglob("*"),
                     *ROOT.joinpath("tests/object_array_refs").rglob("*"),
                     *ROOT.joinpath("tests/function_forks").rglob("*"),
                     *ROOT.joinpath("tests/event_aliases").rglob("*"),
                     *ROOT.joinpath("tests/string_replication").rglob("*"),
                     *ROOT.joinpath("tests/function_termination").rglob("*"),
                     *ROOT.joinpath("tests/associative_refs").rglob("*"),
                     *ROOT.joinpath("tests/runtime_windows").rglob("*"),
                     *ROOT.joinpath("tests/function_locals").rglob("*"),
                     *ROOT.joinpath("tests/scalar_dispatch").rglob("*"),
                     *ROOT.joinpath("tests/nba_storage").rglob("*"),
                     *ROOT.joinpath("tests/string_control").rglob("*"),
                     *ROOT.joinpath("tests/string_integer").rglob("*"),
                     *ROOT.joinpath("tests/final_bind").rglob("*"),
                     *ROOT.joinpath("tests/testbench_io").rglob("*"),
                     *ROOT.joinpath("tests/file_io").rglob("*"),
                     *ROOT.joinpath("tests/binary_io").rglob("*"),
                     *ROOT.joinpath("tests/formatted_scan").rglob("*"),
                     *ROOT.joinpath("tests/cases_archive").rglob("*"),
                     *ROOT.joinpath("tests/cases_hierarchical_writes").rglob("*"),
                     *ROOT.joinpath("tests/hierarchy_writes").rglob("*"),
                     *ROOT.joinpath("tests/function_boundaries").rglob("*"),
                     *ROOT.joinpath("tests/system_functions").rglob("*"),
                     *ROOT.joinpath("tests/complex_report2").rglob("*"),
                     *ROOT.joinpath("tests/report_v3").rglob("*"),
                     *ROOT.joinpath("tests/interfaces").rglob("*"),
                     *ROOT.joinpath("tests/interface_subroutines").rglob("*"),
                     *ROOT.joinpath("tests/modport_prototypes").rglob("*"),
                     *ROOT.joinpath("tests/sampled_values").rglob("*"),
                     *ROOT.joinpath("tests/complex_report").rglob("*"),
                     *ROOT.joinpath("tests/sdf_task").rglob("*"),
                     *ROOT.joinpath("tests/sdf_runtime").rglob("*"),
                     ROOT / "tests/sdf/cli.py",
                     ROOT / "experiments/waveform/dwf.py", ROOT / "tests/gate_source/regression.py",
                     ROOT / "tests/waveform/reader.py", *ROOT.joinpath("cmake").rglob("*"), *ROOT.joinpath("src").rglob("*"),
                     *ROOT.joinpath("include").rglob("*.hpp"), *ROOT.joinpath("include").rglob("*.h"),
                     *ROOT.joinpath("parsers").rglob("*")})
    if check_groups:
        inputs = sorted(set(inputs) | {p for group in check_groups for p in (ROOT / "tests" / group).rglob("*")})
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in inputs if p.is_file() and
              "__pycache__" not in p.parts and not any(x.startswith("build") for x in p.relative_to(ROOT).parts)}
    source_hash = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    release = prefix / "releases" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + source_hash[:12])
    release.mkdir(parents=True)
    runtime = release / "runtime"
    runtime.mkdir()
    for name in HEADERS:
        shutil.copy2(ROOT / "include/dsim" / (name + ".hpp"), runtime)
    shutil.copy2(ROOT / "include/dsim/svdpi.h", runtime / "svdpi.h")
    report = {"status": "BUILDING", "source_sha256": source_hash, "inputs": hashes,
              "command_timeout_seconds": command_timeout,
              "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)),
              "release": str(release), "entry": str(prefix / "bin/dsim"), "check_scope": list(check_groups) if check_groups else "full", "smoke": {}}
    def run(command, label, cwd=release):
        p = subprocess.run(list(map(str, command)), cwd=cwd, capture_output=True, text=True, timeout=command_timeout,
                           env=dict(os.environ, DSIM_TEST_COMMAND_TIMEOUT=str(command_timeout)))
        (release / (label + ".stdout")).write_text(p.stdout)
        (release / (label + ".stderr")).write_text(p.stderr)
        if p.returncode:
            raise RuntimeError(f"{label} failed ({p.returncode}); see {release}")
        return p.stdout
    try:
        run(["cmake", "-S", ROOT, "-B", build, "-DCMAKE_BUILD_TYPE=Release", "-DDSIM_RUNTIME_DIR=" + str(runtime)], "configure")
        run(["cmake", "--build", build, "--target", "dsim", "test_verilog_semantic_memory", "parser_bundle_smoke", "liberty_db_test", "-j", "4"], "build")
        binary = release / "dsim"
        shutil.copy2(build / "dsim", binary)
        run([binary, "--help"], "help")
        run([build / "parsers/test_verilog_semantic_memory"], "rtl-parser")
        report["smoke"]["rtl_parser"] = "PASS"
        run([build / "parsers/parser_bundle_smoke", ROOT / "parsers", release], "format-parsers")
        report["smoke"]["format_parsers"] = "PASS"
        run([build / "liberty_db_test", release / "liberty-db-unit"], "liberty-db-unit")
        report["smoke"]["liberty_db_native"] = "PASS"
        if check_groups:
            # Legacy regressions locate their cache beside the candidate binary.
            shutil.copy2(build / "CMakeCache.txt", release / "CMakeCache.txt")
            def check_group(group):
                run([sys.executable, ROOT / "tests" / group / "regression.py", binary,
                     release / group, build / "CMakeCache.txt"], group)
                return group
            with ThreadPoolExecutor(max_workers=check_jobs) as executor:
                pending = [executor.submit(check_group, group) for group in check_groups]
                for future in as_completed(pending):
                    group = future.result()
                    report["smoke"][group] = "PASS"
                    print("PASS release " + group, flush=True)
        else:
            run([sys.executable, ROOT / "tests/class_associative_strings/regression.py", binary, release / "class_associative_strings", build / "CMakeCache.txt"], "class_associative_strings")
            report["smoke"]["class_associative_strings"] = "PASS"
            run([sys.executable, ROOT / "tests/class_events/regression.py", binary, release / "class_events", build / "CMakeCache.txt"], "class_events")
            report["smoke"]["class_events"] = "PASS"
            run([sys.executable, ROOT / "tests/packed_aggregates/regression.py", binary, release / "packed_aggregates", build / "CMakeCache.txt"], "packed_aggregates")
            report["smoke"]["packed_aggregates"] = "PASS"
            run([sys.executable, ROOT / "tests/unpacked_state/regression.py", binary, release / "unpacked_state", build / "CMakeCache.txt"], "unpacked_state")
            report["smoke"]["unpacked_state"] = "PASS"
            run([sys.executable, ROOT / "tests/report3/regression.py", binary, release / "report3", build / "CMakeCache.txt"], "report3")
            report["smoke"]["report3"] = "PASS"
            run([sys.executable, ROOT / "tests/report4/regression.py", binary, release / "report4", build / "CMakeCache.txt"], "report4")
            report["smoke"]["report4"] = "PASS"
            run([sys.executable, ROOT / "tests/report5/regression.py", binary, release / "report5", build / "CMakeCache.txt"], "report5")
            report["smoke"]["report5"] = "PASS"
            for group in ["virtual_interface_calls", "stream_enum_casts", "virtual_interfaces", "stream_targets", "object_scalar_refs", "associative_values", "array_streams", "shared_tasks", "process_lifetime", "associative_refs", "function_termination", "string_replication", "event_aliases", "function_forks", "object_array_refs", "callback_types", "object_format", "swrite", "late_class_binding", "recursive_functions", "class_handle_arrays", "class_dynamic_arrays", "struct_associative", "struct_containers", "class_body_parameters", "mixed_queues", "array_ordering", "integral_folding", "coverage", "string_queues", "multidim_associative", "integral_keys", "clocking", "struct_strings", "chandle", "compilation_types", "constraint_foreach", "typed_for", "ipc", "process_handles", "gap3_containers", "time_literals", "anonymous_enums", "enums", "runtime_array_patterns", "const_variables", "constraint_randomization", "foreach_selections", "foreach_receivers", "const_properties", "nonansi_bodies", "array_locators", "string_casts", "real_values", "parameterized_formals", "class_parameter_lists", "extern_methods", "dpi", "class_access", "array_aliases", "subroutine_labels", "class_static", "string_associative", "function_boundaries", "cases_hierarchical_writes", "hierarchy_writes", "parameterized_classes", "typed_containers", "class_forward", "class_casts", "class_inheritance", "class_objects", "waveform_selection", "uvm_containers", "waveform_pipeline", "budget_resume", "package_exports", "header_imports", "compiled_activation", "comb_leaves", "typed_stores", "wake_dispatch", "comb_regions", "selection_flush", "selection_checks", "scalar_edges", "hierarchical_arrays", "static_net_drives", "compiled_wait", "nba_storage", "scalar_dispatch", "function_locals", "runtime_windows", "wait_rearm", "integral_loops", "string_control", "string_integer", "testbench_io", "binary_io", "file_io", "formatted_scan", "final_bind", "cases_archive", "report6"]:
                run([sys.executable, ROOT / "tests" / group / "regression.py", binary, release / group, build / "CMakeCache.txt"], group)
                report["smoke"][group] = "PASS"
            run([sys.executable, ROOT / "tests/system_functions/regression.py", binary, release / "system_functions", build / "CMakeCache.txt"], "system_functions")
            report["smoke"]["system_functions"] = "PASS"
            sys.path.insert(0, str(ROOT / "tests/waveform"))
            from reader import read, timeline
            fixtures = ROOT / "tests/dynamic_initializers"
            expected = json.loads((fixtures / "expected.json").read_text())
            conversion = ROOT / "tests/array_state_conversion"
            conversion_expected = json.loads((conversion / "expected.json").read_text())
            constructor_expected = json.loads((conversion / "native-only/expected.json").read_text())
            models = [(name, fixtures / (name + ".sv"), expected[name], name == "parallel", 49)
                      for name in ["static", "automatic", "wide", "parallel"]]
            models += [("state-" + name, conversion / (name + ".sv"), conversion_expected[name], name == "parallel", 0x8503)
                       for name in ["copy", "arguments", "parallel"]]
            models += [("state-constructors", conversion / "native-only/constructors.sv", constructor_expected["constructors"], False, 0)]
            fixed = ROOT / "tests/fixed_initializers"
            fixed_expected = json.loads((fixed / "expected.json").read_text())
            models += [("fixed-" + name, fixed / (name + ".sv"), fixed_expected[name], name == "parallel", 0x8602)
                       for name in ["static", "automatic", "parallel"]]
            frontend = ROOT / "tests/frontend_compat"
            frontend_expected = json.loads((frontend / "expected.json").read_text())
            models += [("frontend-" + name, frontend / (name + ".sv"), wanted, name == "packed_parallel", 0x1203)
                       for name, wanted in frontend_expected.items() if name not in ["ref_identifier", "keyword_names"]]
            instance_arrays = ROOT / "tests/instance_arrays"
            instance_expected = json.loads((instance_arrays / "expected.json").read_text())
            models += [("instance-" + name, instance_arrays / (name + ".sv"), wanted, name == "parallel", 0x7303)
                       for name, wanted in instance_expected.items()]
            patterns = ROOT / "tests/assignment_patterns"
            pattern_expected = json.loads((patterns / "expected.json").read_text())
            models += [("pattern-" + name, patterns / (name + ".sv"), wanted, name == "parallel", 0x7403)
                       for name, wanted in pattern_expected.items()]
            streams = ROOT / "tests/streaming"
            stream_expected = json.loads((streams / "expected.json").read_text())
            models += [("stream-" + name, streams / (name + ".sv"), wanted, name == "parallel", 0x7503)
                       for name, wanted in stream_expected.items()]
            reductions = ROOT / "tests/array_reductions"
            reduction_expected = json.loads((reductions / "expected.json").read_text())
            models += [("reduce-" + name, reductions / (name + ".sv"), wanted, name == "parallel", 0x7603)
                       for name, wanted in reduction_expected.items()]
            mappings = ROOT / "tests/reduction_with"
            mapping_expected = json.loads((mappings / "expected.json").read_text())
            models += [("mapreduce-" + name, mappings / (name + ".sv"), wanted, name == "parallel", 0x7703)
                       for name, wanted in mapping_expected.items()]
            for name, source, wanted, parallel, final_value in models:
                flags = ["--threads", "2"] if parallel else []
                run([binary, source, "--wave-support", *flags,
                     "--emit-cpp", release / (name + ".cpp"), "-o", release / (name + "-sim")], name + "-compile")
                output = run([release / (name + "-sim"), "--waveform", release / (name + ".dwf"),
                              "--wave-mode", "ordered"], name + "-run")
                if [x for x in output.splitlines() if x.startswith("TRACE")] != wanted:
                    raise RuntimeError(name + " release TRACE differs")
                if not (release / (name + ".dwf")).stat().st_size:
                    raise RuntimeError(name + " release waveform is empty")
                if parallel:
                    state = timeline(*read(release / (name + ".dwf")))
                    for port in ["one", "two"]:
                        if state[("top", port)][2][-1][1] != (final_value, 0):
                            raise RuntimeError("release parallel output differs: " + port)
                    run([release / (name + "-sim"), "--parallel-stats"], name + "-stats")
                    if '\"partitions\":2' not in (release / (name + "-stats.stderr")).read_text():
                        raise RuntimeError("release did not use two partitions")
                report["smoke"][name] = "PASS"
            for name in ["ref_identifier", "keyword_names"]:
                label = "frontend-" + name
                source = frontend / (name + (".v" if name == "keyword_names" else ".sv"))
                run([binary, source, "--language", "verilog", "--wave-support",
                     "--emit-cpp", release / (label + ".cpp"), "-o", release / (label + "-sim")], label + "-compile")
                output = run([release / (label + "-sim"), "--waveform", release / (label + ".dwf")], label + "-run")
                if [line for line in output.splitlines() if line.startswith("TRACE")] != frontend_expected[name]:
                    raise RuntimeError(label + " release TRACE differs")
                report["smoke"][label] = "PASS"
            run([sys.executable, ROOT / "tests/gate_source/regression.py", binary, release / "gate-smoke"], "gate-smoke")
            report["smoke"]["gate_source_cli"] = "PASS"
            run([sys.executable, ROOT / "tests/reported_cases/regression.py", binary, release / "reported-cases"], "reported-cases")
            report["smoke"]["reported_cases"] = "PASS"
            run([sys.executable, ROOT / "tests/rtl_report/regression.py", binary, release / "rtl-report"], "rtl-report")
            report["smoke"]["rtl_report"] = "PASS"
            run([sys.executable, ROOT / "tests/random_functions/regression.py", binary, release / "random-functions", build / "CMakeCache.txt"], "random-functions")
            report["smoke"]["random_functions"] = "PASS"
            run([sys.executable, ROOT / "tests/rtl_report/v2/regression.py", binary, release / "rtl-report-v2"], "rtl-report-v2")
            report["smoke"]["rtl_report_v2"] = "PASS"
            run([sys.executable, ROOT / "tests/packages/regression.py", binary, release / "packages", build / "CMakeCache.txt"], "packages")
            report["smoke"]["packages"] = "PASS"
            run([sys.executable, ROOT / "tests/strings/regression.py", binary, release / "strings", build / "CMakeCache.txt"], "strings")
            report["smoke"]["strings"] = "PASS"
            run([sys.executable, ROOT / "tests/string_subroutines/regression.py", binary, release / "string_subroutines", build / "CMakeCache.txt"], "string_subroutines")
            report["smoke"]["string_subroutines"] = "PASS"
            run([sys.executable, ROOT / "tests/concurrent_assertions/regression.py", binary, release / "concurrent_assertions", build / "CMakeCache.txt"], "concurrent_assertions")
            report["smoke"]["concurrent_assertions"] = "PASS"
            run([sys.executable, ROOT / "tests/complex_report2/regression.py", binary, release / "complex_report2", build / "CMakeCache.txt"], "complex_report2")
            report["smoke"]["complex_report2"] = "PASS"
            run([sys.executable, ROOT / "tests/comb_partial/regression.py", binary, release / "comb_partial", build / "CMakeCache.txt"], "comb_partial")
            report["smoke"]["comb_partial"] = "PASS"
            run([sys.executable, ROOT / "tests/ascending_packed/regression.py", binary, release / "ascending_packed", build / "CMakeCache.txt"], "ascending_packed")
            report["smoke"]["ascending_packed"] = "PASS"
            run([sys.executable, ROOT / "tests/comb_sensitivity/regression.py", binary, release / "comb_sensitivity", build / "CMakeCache.txt"], "comb_sensitivity")
            report["smoke"]["comb_sensitivity"] = "PASS"
            run([sys.executable, ROOT / "tests/memory_cases/regression.py", binary, release / "memory_cases", build / "CMakeCache.txt"], "memory_cases")
            report["smoke"]["memory_cases"] = "PASS"
            run([sys.executable, ROOT / "tests/sequence_antecedents/regression.py", binary, release / "sequence_antecedents", build / "CMakeCache.txt"], "sequence_antecedents")
            report["smoke"]["sequence_antecedents"] = "PASS"
            run([sys.executable, ROOT / "tests/named_sequences/regression.py", binary, release / "named_sequences", build / "CMakeCache.txt"], "named_sequences")
            report["smoke"]["named_sequences"] = "PASS"
            run([sys.executable, ROOT / "tests/sequence_groups/regression.py", binary, release / "sequence_groups", build / "CMakeCache.txt"], "sequence_groups")
            report["smoke"]["sequence_groups"] = "PASS"
            run([sys.executable, ROOT / "tests/sequence_repetition/regression.py", binary, release / "sequence_repetition", build / "CMakeCache.txt"], "sequence_repetition")
            report["smoke"]["sequence_repetition"] = "PASS"
            run([sys.executable, ROOT / "tests/sequence_delays/regression.py", binary, release / "sequence_delays", build / "CMakeCache.txt"], "sequence_delays")
            report["smoke"]["sequence_delays"] = "PASS"
            run([sys.executable, ROOT / "tests/report_v3/regression.py", binary, release / "report_v3", build / "CMakeCache.txt"], "report_v3")
            report["smoke"]["report_v3"] = "PASS"
            run([sys.executable, ROOT / "tests/interface_subroutines/regression.py", binary, release / "interface_subroutines", build / "CMakeCache.txt"], "interface_subroutines")
            report["smoke"]["interface_subroutines"] = "PASS"
            run([sys.executable, ROOT / "tests/compilation_imports/regression.py", binary, release / "compilation_imports", build / "CMakeCache.txt"], "compilation_imports")
            report["smoke"]["compilation_imports"] = "PASS"
            run([sys.executable, ROOT / "tests/unit_lifetimes/regression.py", binary, release / "unit_lifetimes", build / "CMakeCache.txt"], "unit_lifetimes")
            report["smoke"]["unit_lifetimes"] = "PASS"
            run([sys.executable, ROOT / "tests/modport_prototypes/regression.py", binary, release / "modport_prototypes", build / "CMakeCache.txt"], "modport_prototypes")
            report["smoke"]["modport_prototypes"] = "PASS"
            run([sys.executable, ROOT / "tests/interfaces/regression.py", binary, release / "interfaces", build / "CMakeCache.txt"], "interfaces")
            report["smoke"]["interfaces"] = "PASS"
            run([sys.executable, ROOT / "tests/sampled_values/regression.py", binary, release / "sampled_values", build / "CMakeCache.txt"], "sampled_values")
            report["smoke"]["sampled_values"] = "PASS"
            run([sys.executable, ROOT / "tests/complex_report/regression.py", binary, release / "complex_report", build / "CMakeCache.txt"], "complex_report")
            report["smoke"]["complex_report"] = "PASS"
        for path, want in hashes.items():
            if digest(ROOT / path) != want:
                raise RuntimeError("source changed while publishing: " + path)
        for name in HEADERS:
            if digest(runtime / (name + ".hpp")) != hashes["include/dsim/" + name + ".hpp"]:
                raise RuntimeError("runtime snapshot mismatch: " + name)
        if digest(runtime / "svdpi.h") != hashes["include/dsim/svdpi.h"]:
            raise RuntimeError("runtime snapshot mismatch: svdpi.h")
        report.update(status="PASS", binary_sha256=digest(binary))
        report["active"] = not stage_only
        (release / "release.json").write_text(json.dumps(report, indent=2) + "\n")
        if stage_only:
            print(json.dumps({k: report[k] for k in ["status", "active", "entry", "release", "git_commit", "source_sha256", "binary_sha256", "smoke"]}, indent=2))
            return
        entry = prefix / "bin/dsim"
        entry.parent.mkdir(parents=True, exist_ok=True)
        # Update just one symlink after every check passed. An earlier release stays intact.
        fd, tmp = tempfile.mkstemp(prefix=".dsim-", dir=entry.parent)
        os.close(fd)
        os.unlink(tmp)
        try:
            os.symlink(os.path.relpath(binary, entry.parent), tmp)
            os.replace(tmp, entry)
        finally:
            if os.path.lexists(tmp):
                os.unlink(tmp)
        print(json.dumps({k: report[k] for k in ["status", "entry", "release", "git_commit", "source_sha256", "binary_sha256", "smoke"]}, indent=2))
    except Exception as error:
        report.update(status="FAIL", failure=str(error))
        (release / "release.json").write_text(json.dumps(report, indent=2) + "\n")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, default=Path.home() / "vibe-coding/dsim-test")
    parser.add_argument("--build", type=Path, default=ROOT / "build-stable")
    parser.add_argument("--stage-only", action="store_true", help="Build and verify a release without changing bin/dsim")
    parser.add_argument("--check-group", action="append", choices=["virtual_interface_calls", "stream_enum_casts", "virtual_interfaces", "stream_targets", "object_scalar_refs", "associative_values", "array_streams", "shared_tasks", "process_lifetime", "associative_refs", "function_termination", "string_replication", "event_aliases", "function_forks", "object_array_refs", "callback_types", "object_format", "swrite", "late_class_binding", "queue_slices", "array_equality", "type_reflection", "uvm_call_values", "recursive_functions", "class_handle_arrays", "class_dynamic_arrays", "class_associative_strings", "class_events", "named_events", "qualified_named_events", "function_events", "conditional_events", "struct_associative", "struct_containers", "class_body_parameters", "mixed_queues", "array_ordering", "integral_folding", "coverage", "string_queues", "multidim_associative", "integral_keys", "clocking", "unpacked_state", "packed_aggregates", "struct_strings", "chandle", "compilation_types", "constraint_foreach", "typed_for", "ipc", "process_handles", "random_functions", "gap3_containers", "time_literals", "anonymous_enums", "enums", "runtime_array_patterns", "const_variables", "constraint_randomization", "foreach_selections", "foreach_receivers", "const_properties", "nonansi_bodies", "array_locators", "string_casts", "real_values", "parameterized_formals", "class_parameter_lists", "extern_methods", "dpi", "class_access", "array_aliases", "subroutine_labels", "class_static", "string_associative", "preprocess", "fixed_initializers", "dynamic_initializers", "parameterized_classes", "typed_containers", "class_forward", "class_casts", "class_inheritance", "class_objects", "event_expressions", "waveform_selection", "uvm_containers", "waveform_pipeline", "dynamic_arrays", "dynamic_arguments", "reduction_with", "compilation_imports", "unit_lifetimes", "package_lifetimes", "modport_prototypes", "interface_subroutines", "sequence_antecedents", "memory_cases", "named_sequences", "sequence_groups", "sequence_repetition", "sequence_delays", "concurrent_assertions", "sampled_values", "budget_resume", "package_exports", "header_imports", "packages", "interfaces", "frontend_compat", "named_types", "compiled_activation", "comb_leaves", "typed_stores", "wake_dispatch", "comb_regions", "selection_flush", "selection_checks", "scalar_edges", "hierarchical_arrays", "static_net_drives", "compiled_wait", "nba_storage", "scalar_dispatch", "function_locals", "runtime_windows", "wait_rearm", "compiler_options", "parallel_arithmetic", "runtime_scalar_fast", "memory", "binary_io", "file_io", "formatted_scan", "liberty_db", "gate_source", "string_subroutines", "strings", "subroutines",
                        "call_arguments", "automatic_subroutines", "ref_arguments", "const_ref", "report3", "report4", "report5", "integral_loops", "string_control", "string_integer", "testbench_io", "final_bind", "cases_archive", "cases_hierarchical_writes", "hierarchy_writes", "function_boundaries", "comb_partial", "report6"],
                        help="Run selected affected regression groups; parser and format checks always run. Default: full suite.")
    parser.add_argument("--check-jobs", type=int, choices=range(1, 17), default=1, help="Concurrent independent selected regression groups (build remains single).")
    parser.add_argument("--command-timeout", type=int, default=900,
                        help="Timeout in seconds for each build/check command (default: 900).")
    args = parser.parse_args()
    if args.command_timeout <= 0:
        parser.error("--command-timeout must be positive")
    publish(args.prefix, args.build, list(dict.fromkeys(args.check_group)) if args.check_group else None,
            args.stage_only, args.check_jobs, args.command_timeout)
