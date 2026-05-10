# Governance Simulation (Human vs AI)

Minimal runnable simulation framework with exportable HTML reports.

## Quick start

Run paired comparison (same seed, same initial conditions):

```bash
python main.py --mode pair --ticks 400 --agents 400 --seed 42 --out outputs
```

Run human vs strong AI comparison:

```bash
python main.py --mode pair_strong --ticks 400 --agents 400 --seed 42 --out outputs
```

Run a single governance mode:

```bash
python main.py --mode single --governance human --ticks 400 --agents 400 --seed 42 --out outputs
python main.py --mode single --governance ai --ticks 400 --agents 400 --seed 42 --out outputs
```

Regenerate only the aggregate report (after deleting or adding run folders):

```bash
python main.py --mode aggregate --out outputs
```

## Output files

Per run directory (e.g. `outputs/human_seed_42_20260504_173000/`):

- `metrics_timeseries.csv`: per-tick metrics
- `summary.json`: final-window aggregated metrics and config
- `report.html`: visualization report (Plotly)
- `report_offline.html`: offline-friendly report

At output root (`outputs/`):

- `aggregate_report.html`: single combined report (same-name overwrite)

## Main modules

- `config.py`: simulation parameters
- `agent.py`: agent state model
- `governance.py`: human/ai governance logic
- `model.py`: tick pipeline orchestration
- `metrics.py`: utility metrics
- `experiments.py`: run and export logic
- `report.py`: HTML report generator
- `main.py`: CLI entry

## Notes

- The HTML report is generated from exported CSV/JSON so visual and simulation layers are decoupled.
- You can customize report style and chart structure in `report.py` without changing simulation logic.
- The aggregate report auto-scans all valid run folders under `outputs/`.

## Chinese documentation

- Detailed Chinese guide: `中文说明文档.md`
