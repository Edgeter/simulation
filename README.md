# Governance Simulation (Human vs AI)

This repository provides a reproducible simulation framework for comparative analysis of governance mechanisms under controlled initial conditions. The current implementation supports Human governance, AI governance, and report-oriented experiment workflows.

## Project Scope

- Controlled comparison under shared initial states and identical random seeds
- Tick-based social dynamics with governance intervention and redistribution
- Export of per-run metrics, summary statistics, and visualization reports
- Aggregate reporting across multiple historical runs

## Usage

Run paired comparison (same seed and initial conditions):

```bash
python main.py --mode pair --ticks 400 --agents 400 --seed 42 --out outputs
```

Run Human vs strong-AI comparison:

```bash
python main.py --mode pair_strong --ticks 400 --agents 400 --seed 42 --out outputs
```

Run a single governance mode:

```bash
python main.py --mode single --governance human --ticks 400 --agents 400 --seed 42 --out outputs
python main.py --mode single --governance ai --ticks 400 --agents 400 --seed 42 --out outputs
```

Regenerate only the aggregate report (after adding/removing run folders):

```bash
python main.py --mode aggregate --out outputs
```

## Output Artifacts

Per-run directory (e.g. `outputs/human_seed_42_20260504_173000/`):

- `metrics_timeseries.csv`: per-tick metrics
- `summary.json`: final-window aggregated metrics and configuration snapshot
- `report.html`: interactive visualization report (Plotly)
- `report_offline.html`: offline-compatible report

At output root (`outputs/`):

- `aggregate_report.html`: combined report with same-name overwrite behavior

## Repository Structure

- `config.py`: simulation parameters
- `agent.py`: agent state model
- `governance.py`: Human/AI governance logic
- `model.py`: tick pipeline orchestration
- `metrics.py`: utility metrics
- `experiments.py`: run and export logic
- `report.py`: HTML report generator
- `main.py`: CLI entry

## Implementation Notes

- HTML reports are generated from exported CSV/JSON artifacts; simulation and visualization layers are decoupled.
- Report style and chart structure can be adjusted in `report.py` without modifying the simulation core.
- The aggregate report automatically scans valid run directories under `outputs/`.

## Documentation

- Detailed Chinese guide: `中文说明文档.md`
- Project summary (Chinese): `PROJECT_SUMMARY_CN.md`
