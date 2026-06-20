"""Reusable multi-template fuzz harnesses for simulator parity."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from rtlgen_x.sim.cpp_backend import Assignment, BinaryExpr, CppBackendScaffold, Signal, SignalRef, SimModule
from rtlgen_x.sim.trace import RandomParityConfig, RandomParityHarnessReport, run_random_parity_fuzz


@dataclass(frozen=True)
class FuzzTemplate:
    name: str
    module: SimModule


@dataclass(frozen=True)
class FuzzSuiteReport:
    reports: Tuple[RandomParityHarnessReport, ...]

    @property
    def all_matched(self) -> bool:
        return all(report.parity.matched for report in self.reports)


def build_fuzz_templates() -> Tuple[FuzzTemplate, ...]:
    return (
        FuzzTemplate(
            name="accum_xor",
            module=SimModule(
                name="fuzz_accum_xor",
                signals=(
                    Signal("a", width=8, kind="input"),
                    Signal("b", width=8, kind="input"),
                    Signal("acc", width=8, kind="state", init=3),
                    Signal("out", width=8, kind="output"),
                ),
                assignments=(
                    Assignment("out", BinaryExpr("^", BinaryExpr("+", SignalRef("acc"), SignalRef("a")), SignalRef("b"))),
                    Assignment("acc", BinaryExpr("+", SignalRef("acc"), SignalRef("a")), phase="seq"),
                ),
                outputs=("out",),
            ),
        ),
        FuzzTemplate(
            name="shift_mix",
            module=SimModule(
                name="fuzz_shift_mix",
                signals=(
                    Signal("inp", width=8, kind="input"),
                    Signal("shamt", width=3, kind="input"),
                    Signal("state", width=8, kind="state", init=1),
                    Signal("out", width=8, kind="output"),
                ),
                assignments=(
                    Assignment("out", BinaryExpr("^", BinaryExpr("<<", SignalRef("inp"), SignalRef("shamt")), SignalRef("state"))),
                    Assignment("state", BinaryExpr("+", SignalRef("state"), SignalRef("inp")), phase="seq"),
                ),
                outputs=("out",),
            ),
        ),
    )


def run_fuzz_suite(
    *,
    config: RandomParityConfig = RandomParityConfig(),
    builder: Optional[CppBackendScaffold] = None,
    build_root: Optional[Path | str] = None,
    templates: Optional[Sequence[FuzzTemplate]] = None,
) -> FuzzSuiteReport:
    runtime_builder = builder if builder is not None else CppBackendScaffold()
    root = Path(build_root) if build_root is not None else None
    reports: List[RandomParityHarnessReport] = []
    for template in tuple(templates or build_fuzz_templates()):
        build_dir = None if root is None else root / template.name
        reports.append(
            run_random_parity_fuzz(
                template.module,
                config=config,
                builder=runtime_builder,
                build_dir=build_dir,
            )
        )
    return FuzzSuiteReport(reports=tuple(reports))
