from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Optional

from config import SimulationConfig
from model import SocietyModel


def run_single(cfg: SimulationConfig, out_dir: Path, run_name: str) -> Dict:
    run_dir = out_dir / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    model = SocietyModel(cfg)
    rows = model.run()
    summary = model.final_summary()

    csv_path = run_dir / "metrics_timeseries.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    json_path = run_dir / "summary.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=True, indent=2)

    return {
        "run_dir": str(run_dir),
        "csv": str(csv_path),
        "summary": str(json_path),
    }


def run_pair(
    base_cfg: SimulationConfig,
    out_dir: Path,
    seed: int,
    run_tag: Optional[str] = None,
    ai_mode: str = "ai",
) -> List[Dict]:
    human_cfg = SimulationConfig(**{**base_cfg.__dict__, "governance_type": "human", "seed": seed})
    ai_cfg = SimulationConfig(**{**base_cfg.__dict__, "governance_type": ai_mode, "seed": seed})

    tag = f"_{run_tag}" if run_tag else ""
    res1 = run_single(human_cfg, out_dir, f"human_seed_{seed}{tag}")
    res2 = run_single(ai_cfg, out_dir, f"{ai_mode}_seed_{seed}{tag}")
    return [res1, res2]
