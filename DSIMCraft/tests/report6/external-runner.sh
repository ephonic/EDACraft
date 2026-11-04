#!/bin/zsh
# probes2 runner: compile+run each probe, classify
DSIM=../../../bin/dsim
cd "$(dirname "$0")"
rm -f results.txt
integer failures=0

probe() {   # name, expected-verdict, command...
    local name=$1 want=$2; shift 2
    local out; local rc=0; out=$("$@" 2>&1) || rc=$?
    if [[ $rc -eq 0 ]] && echo "$out" | grep -Fq "$want"; then
        printf "%-24s PASS\n" "$name" >> results.txt
    else
        (( failures += 1 ))
        printf "%-24s CHECK  (%s)\n" "$name" "$(echo "$out" | tail -1 | cut -c1-80)" >> results.txt
    fi
}

DS=$DSIM
probe p21_sra_cond    "PROBE_SRA: PASS" sh -c "$DS --top tb -o s21 p21_sra_cond.sv >/dev/null 2>&1 && ./s21"
probe p22_varidx_nba  "PROBE_VARRD: ok"                  sh -c "$DS --top tb -o s22 p22_varidx_nba.sv >/dev/null 2>&1 && ./s22"
probe p23_multi_always "second always fired"             sh -c "$DS --top tb -o s23 p23_multi_always.sv >/dev/null 2>&1 && ./s23"
probe p24_vcd_text    "VCD_OK"                sh -c "$DS --wave-support --top top -o s24 p24_vcd.sv >/dev/null 2>&1 && ./s24 --waveform report6-wave-$$.vcd && grep -q timescale report6-wave-$$.vcd && echo VCD_OK"
probe p25_cli         "CLI_PROBE: ok W_INC=42"           sh -c "$DS --top top -o s25 +incdir+inc +define+DEF_SET p25_cli_inc.sv >/dev/null 2>&1 && ./s25"
probe p25_flist       "CLI_PROBE: ok W_INC=42"           sh -c "$DS --top top -o s25f -f flist.f +incdir+inc +define+DEF_SET >/dev/null 2>&1 && ./s25f"
probe p26_sdf_check   "cells\":4"                        sh -c "$DS --sdf-check timing.sdf"
probe p26_sdf_bind    "bound_entries\":7"                sh -c "$DS --sdf-bind-check timing.sdf --gate-netlist netlist.v --gate-top top --liberty cells.lib --gate-models models.v --sdf-tick 1ps"
probe p26_sdf_annot   "GATE_PROBE: y=1"                  sh -c "$DS --top tb -o s26a --sdf-annotate timing.sdf --gate-netlist netlist.v --gate-top top --gate-models models.v --liberty cells.lib p26_tb.sv >/dev/null 2>&1 && ./s26a"
probe p27_signed_tern "PROBE_CONTEXT: PASS"                          sh -c "$DS --top tb -o s27 p27_signed_ternary.sv >/dev/null 2>&1 && ./s27"
probe p28_string_mix "PROBE_STRMIX: ok"                  sh -c "$DS --top tb -o s28 p28_string_mix.sv >/dev/null 2>&1 && ./s28"
probe p29_context "PROBE_CONTEXT: PASS" sh -c "$DS --top tb -o s29 p29_ternary_context.sv >/dev/null 2>&1 && ./s29"
cat results.txt
exit $(( failures > 0 ))
