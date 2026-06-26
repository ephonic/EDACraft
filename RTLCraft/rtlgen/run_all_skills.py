"""
rtlgen.run_all_skills — Thin wrapper around SkillPPARunner.

All logic lives in rtlgen.skill_ppa.SkillPPARunner.
This module exists only for backward compatibility.
"""
from __future__ import annotations

import sys
import os

from rtlgen.skill_ppa import (
    SkillPPARunner,
    SkillPipelineResult,
    discover_skills,
    ModulePPAReport,
    StageResult,
)

# Re-export for backward compatibility
__all__ = [
    "SkillPPARunner",
    "SkillPipelineResult",
    "discover_skills",
    "ModulePPAReport",
    "StageResult",
    "run_skill",
    "run_all_skills",
]


def run_skill(
    skill_name: str,
    output_dir: str = "generated_skill_ppa",
    stages: list[str] | None = None,
    max_logic_depth: int = 5,
    max_iterations: int = 10,
) -> SkillPipelineResult:
    """Run full pipeline for one skill.

    Args:
        skill_name: Skill name (e.g. "riscv64_soc")
        output_dir: Output directory for generated RTL
        stages: Specific stages to run (None = all)
        max_logic_depth: PPA max logic depth target
        max_iterations: Max PPA optimization iterations

    Returns:
        SkillPipelineResult with stage results, module reports, and RTL files.
    """
    runner = SkillPPARunner(skill_name)
    return runner.run(
        output_dir=output_dir,
        max_logic_depth=max_logic_depth,
        max_iterations=max_iterations,
        stages=stages,
    )


def run_all_skills(
    output_dir: str = "generated_skill_ppa",
    skills_filter: list[str] | None = None,
    stages: list[str] | None = None,
    max_logic_depth: int = 5,
    max_iterations: int = 10,
    skills_dir: str | None = None,
) -> dict[str, SkillPipelineResult]:
    """Run all discoverable skills through the pipeline.

    Returns:
        Dict mapping skill name to SkillPipelineResult.
    """
    all_skills = discover_skills(skills_dir)
    if skills_filter:
        all_skills = [s for s in all_skills if s in skills_filter]

    results = {}
    for skill_name in all_skills:
        runner = SkillPPARunner(skill_name)
        results[skill_name] = runner.run(
            output_dir=output_dir,
            max_logic_depth=max_logic_depth,
            max_iterations=max_iterations,
            stages=stages,
        )

    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    passed = sum(1 for r in results.values() if r.success)
    failed = sum(1 for r in results.values() if not r.success)
    for name, r in sorted(results.items()):
        status = "PASS" if r.success else "FAIL"
        stages_str = ", ".join(sr.stage_name for sr in r.stage_results if sr.passed)
        print(f"  [{status}] {name}: {stages_str}")
    print(f"\n  {passed} passed, {failed} failed out of {len(results)} skills")

    return results


# -----------------------------------------------------------------------
# CLI entry point (python -m rtlgen.run_all_skills)
# -----------------------------------------------------------------------

def _main():
    import argparse

    parser = argparse.ArgumentParser(description="Run all skills through the RTL pipeline")
    parser.add_argument("--skill", type=str, nargs="*", help="Run specific skill(s)")
    parser.add_argument("--list", action="store_true", help="List discoverable skills")
    parser.add_argument("--output", type=str, default="generated_skill_ppa", help="Output directory")
    parser.add_argument("--stage", type=str, nargs="*",
                        choices=SkillPPARunner.ALL_STAGES,
                        help="Run specific stages only")
    parser.add_argument("--depth", type=int, default=5, help="Max logic depth target")
    parser.add_argument("--iterations", type=int, default=10, help="Max PPA iterations")
    parser.add_argument("--skills-dir", type=str, help="Skills directory")

    args = parser.parse_args()

    if args.list:
        skills = discover_skills(args.skills_dir)
        print(f"Discoverable skills ({len(skills)}):")
        for s in skills:
            skill_path = os.path.join(args.skills_dir or os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills"
            ), s)
            modules = []
            for m in ["dsl_modules", "arch_templates", "functional", "cycle_level", "behaviors", "models", "skeleton_templates"]:
                if os.path.isfile(os.path.join(skill_path, f"{m}.py")):
                    modules.append(m)
            print(f"  - {s}: {', '.join(modules)}")
        return

    results = run_all_skills(
        output_dir=args.output,
        skills_filter=args.skill,
        stages=args.stage,
        max_logic_depth=args.depth,
        max_iterations=args.iterations,
        skills_dir=args.skills_dir,
    )

    if any(not r.success for r in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    _main()
