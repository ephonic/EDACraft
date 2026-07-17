#!/usr/bin/env python3
"""bench_summary.py — V2-γ C3 JSON → markdown 汇总

用法:
    python tools/bench_summary.py build/bench_<timestamp>.json [--out build/bench_summary.md]

读取 rfsim_tests 在 RFSIM_BENCH_JSON=1 下生成的 bench_*.json，输出 markdown 表格，
按 wall_ms 降序，标记前 3 名 wall-time 主导项供 C4 perf 采样聚焦。
"""
import argparse
import json
import os
import sys
from typing import List, Dict


def load_records(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path}: 期望 JSON 数组")
    return data


def fmt(v, prec=3):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.{prec}f}"
    return str(v)


def to_md(records: List[Dict]) -> str:
    # 按 wall_ms 降序
    rs = sorted(records, key=lambda r: r.get("wall_ms", 0.0), reverse=True)
    lines = []
    lines.append("# rfsim bench 汇总\n")
    lines.append(f"共 {len(rs)} 条用例。按 wall_ms 降序，前 3 名标记 ★（C4 perf 采样聚焦项）。\n")
    lines.append("")
    lines.append("| # | suite | case | phase | wall_ms | newton_iter | klu_factor_ms | klu_solve_ms | peak_rss_mb |")
    lines.append("|---|-------|------|-------|---------|-------------|---------------|--------------|-------------|")
    for i, r in enumerate(rs, 1):
        star = " ★" if i <= 3 else ""
        lines.append(
            f"| {i}{star} | {r.get('suite','-')} | {r.get('case','-')} | "
            f"{r.get('phase','-')} | {fmt(r.get('wall_ms'))} | "
            f"{r.get('newton_iter','-')} | {fmt(r.get('klu_factor_ms'))} | "
            f"{fmt(r.get('klu_solve_ms'))} | {fmt(r.get('peak_rss_mb'))} |"
        )
    lines.append("")
    # Top-3 分析段落
    lines.append("## C4 perf 采样聚焦项（wall-time 前 3）\n")
    for i, r in enumerate(rs[:3], 1):
        lines.append(
            f"{i}. **{r.get('suite','-')}.{r.get('case','-')}** "
            f"({r.get('phase','-')}): wall={fmt(r.get('wall_ms'))} ms, "
            f"newton_iter={r.get('newton_iter','-')}, "
            f"klu_factor={fmt(r.get('klu_factor_ms'))} ms, "
            f"klu_solve={fmt(r.get('klu_solve_ms'))} ms, "
            f"rss={fmt(r.get('peak_rss_mb'))} MB"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json", help="bench_<timestamp>.json 路径")
    ap.add_argument("--out", help="输出 markdown 路径（默认 stdout）")
    args = ap.parse_args()

    if not os.path.exists(args.json):
        print(f"错误: {args.json} 不存在", file=sys.stderr)
        sys.exit(1)

    records = load_records(args.json)
    md = to_md(records)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"已写入 {args.out}")
    else:
        print(md)


if __name__ == "__main__":
    main()
