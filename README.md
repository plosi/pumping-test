# pumping-test

A Python library and CLI for interpreting single-well pumping tests on water wells, following the ICRC guidelines *"Technical Review — Practical Guidelines for Test Pumping in Water Wells"* (2011).

## Overview

This project provides a clean, layered Python implementation of three standard pumping test analysis methods:

- **Step-drawdown test** — Hantush-Bierschenk method to separate aquifer and well losses
- **Constant-rate test** — Cooper-Jacob straight-line method to estimate transmissivity
- **Recovery test** — Theis recovery method

The codebase is structured as a pure analysis library with no UI dependencies, wrapped by a Typer CLI. A web interface is planned as a future layer on top of the same library.

## Project structure

```
pumping_test/
├── models.py               # Domain dataclasses: Borehole, Measurement, Step, PumpingTest, results
├── analysis/
│   ├── constant_rate.py    # Cooper-Jacob analysis
│   ├── recovery.py         # Theis recovery analysis
│   └── step_drawdown.py    # Hantush-Bierschenk analysis
├── in_out/
│   └── csv_reader.py       # CSV parsing and validation → PumpingTest
├── plotting/
│   ├── constant_rate.py    # Preview and semi-log plots
│   ├── recovery.py         # Preview and semi-log plots
│   ├── step_drawdown.py    # Preview and specific drawdown plots
│   └── utils.py            # deliver_plot / deliver_plots helpers
├── config/
│   ├── schema.py           # Pydantic config schemas
│   ├── loader.py           # JSON/YAML config loader
│   └── validator.py        # Config validation
├── cli.py                  # Typer CLI entry point
```

## Installation

```bash
git clone https://github.com/plosi/pumping-test.git
cd pumping-test
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## CSV format

All commands accept a CSV file with the following required columns:

| Column | Description |
|---|---|
| `time_min` | Elapsed time since start of test [minutes] |
| `level_m` | Water level measured from datum [m below datum] |

## CLI usage

### Constant-rate test

```bash
python cli.py constant-rate data.csv \
  --static-level 10.5 \
  --flowrate 24.0 \
  --borehole-name BH01
```

Optional flags:
- `--fit-start` / `--fit-end` — control the fit window (row indices)
- `--output preview.html --output analysis.html` — save plots to file instead of opening in browser

### Recovery test

```bash
python cli.py recovery data.csv \
  --static-level 10.5 \
  --flowrate 24.0 \
  --end-of-pumping 600 \
  --borehole-name BH01
```

### Step-drawdown test

```bash
python cli.py step-drawdown data.csv \
  --static-level 10.5 \
  --step "4.2,120" \
  --step "9.8,240" \
  --step "17.5,360" \
  --step "22.1,480" \
  --borehole-name BH01
```

Each `--step` flag takes a `"flowrate,end_time"` pair (m³/h and minutes respectively).

### Run from config file

All three tests can be configured in a single JSON or YAML file and run together:

```bash
python cli.py run borehole_config.yaml
```

### Plot output

All commands produce two plots, step-drawdown produces 3. By default these open in the browser. To save to files, provide one `--output` path per plot in order:

```bash
python cli.py constant-rate data.csv \
  --static-level 10.5 --flowrate 24.0 \
  --output preview.html \
  --output semilog.html
```

Supported formats: `.html` (interactive), `.png`, `.svg`, `.pdf` (static, requires `kaleido`).


## Methods and reference

| Test | Method | Reference |
|---|---|---|
| Constant-rate | Cooper-Jacob straight-line | ICRC (2011), Section 5 |
| Recovery | Theis recovery | ICRC (2011), Section 6 |
| Step-drawdown | Hantush-Bierschenk | ICRC (2011), Section 4 |

Yield estimates follow MacDonald et al. (2005).

## License

MIT