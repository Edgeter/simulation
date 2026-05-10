from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from config import SimulationConfig
from experiments import run_pair, run_single
from report import generate_aggregate_report, generate_report


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Governance simulation runner")
    p.add_argument("--mode", choices=["single", "pair", "pair_strong", "aggregate"], default="pair")
    p.add_argument("--governance", choices=["human", "ai", "ai_strong"], default="human")
    p.add_argument("--ticks", type=int, default=400)
    p.add_argument("--agents", type=int, default=400)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=str, default="outputs")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = SimulationConfig(n_ticks=args.ticks, n_agents=args.agents, seed=args.seed, governance_type=args.governance)
    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.mode == "aggregate":
        aggregate_path = generate_aggregate_report(out_dir)
        print(f"综合报告已生成: {aggregate_path}")
        return

    if args.mode == "single":
        result = run_single(cfg, out_dir, f"{cfg.governance_type}_seed_{cfg.seed}_{run_tag}")
        report_path = generate_report(Path(result["run_dir"]))
        print(f"Run completed: {result['run_dir']}")
        print(f"Report: {report_path}")
    else:
        ai_mode = "ai_strong" if args.mode == "pair_strong" else "ai"
        results = run_pair(cfg, out_dir, args.seed, run_tag=run_tag, ai_mode=ai_mode)
        for r in results:
            report_path = generate_report(Path(r["run_dir"]))
            print(f"Run completed: {r['run_dir']}")
            print(f"Report: {report_path}")

    aggregate_path = generate_aggregate_report(out_dir)
    print(f"综合报告已更新: {aggregate_path}")


if __name__ == "__main__":
    main()
