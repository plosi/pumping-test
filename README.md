# pumping-test

A Python library, CLI, and web application for interpreting single-well pumping tests on water wells,
following the ICRC guidelines *"Technical Review — Practical Guidelines for Test Pumping in Water
Wells"* (2011).

Developed by [Paolo Losi](https://github.com/plosi) | [MIT License](LICENSE)

---

## Overview

This tool supports field hydrogeologists and water engineers in the office interpretation of borehole
pumping test data. It implements three standard single-well test analysis methods, produces interactive
charts, quantitative results tables, plain-language interpretations, and downloadable DOCX reports
suitable for inclusion in technical notes and design documents.

### Supported test types

| Test | Method | Key outputs |
|---|---|---|
| Constant-rate | Cooper-Jacob straight-line | Transmissivity, estimated yield (supports dual fit) |
| Recovery | Theis recovery method | Transmissivity, estimated yield, % recovery |
| Step-drawdown | Hantush-Bierschenk | Aquifer/well loss coefficients, critical yield, step efficiency |

---

## Project structure

```
pumping_test/
├── models.py                   # Domain dataclasses: Borehole, Measurement, Step,
│                               # PumpingTest, DrawdownFit, result objects
├── analysis/
│   ├── constant_rate.py        # Cooper-Jacob analysis (supports dual fit windows)
│   ├── recovery.py             # Theis recovery analysis
│   ├── step_drawdown.py        # Hantush-Bierschenk analysis
│   └── interpretation.py       # Plain-language result interpretation
├── in_out/
│   └── csv_reader.py           # CSV parsing and validation → PumpingTest
│   └── report.py               # DOCX report generation (python-docx)
├── plotting/
│   ├── common.py               # Shared colour palette and layout helpers
│   ├── constant_rate.py        # Raw preview + semi-log plot (dual fit support)
│   ├── recovery.py             # Raw preview + t/t' semi-log plot
│   ├── step_drawdown.py        # Raw preview + specific drawdown + losses vs Q
│   └── utils.py                # deliver_plot / deliver_plots helpers
├── config/
│   ├── schema.py               # Pydantic config schemas
│   ├── loader.py               # JSON / YAML config file loader
│   └── validator.py            # Config validation
├── app/
│   ├── main.py                 # Shiny App entry point
│   ├── layout.py               # Full UI definition (sidebar + tabs)
│   ├── server.py               # Reactive server logic
│   └── runner.py               # Shared orchestration layer (CLI + Shiny)
├── data/                       # Sample data files
├── templates/                  # CSV template files
├── cli.py                      # Typer CLI entry point
├── app.py                      # Deployment shim → app/main.py
└── pyproject.toml
```

---

## Installation

Requires **Python 3.11+**. [uv](https://github.com/astral-sh/uv) is recommended for environment
management.

```bash
git clone https://github.com/plosi/pumping-test.git
cd pumping-test

# With uv (recommended)
uv sync

# Or with pip
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .
```

---

## Web application

The web application is the primary interface. It is built with
[Shiny for Python](https://shiny.posit.co/py/) and designed for office use by analysts
interpreting field data received from borehole testing campaigns.

### Running locally

```bash
shiny run app/main.py --reload
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

### Application layout

The app uses a persistent sidebar and tabbed main panel layout.

**Sidebar — always visible**

- Test type selector (constant-rate / recovery / step-drawdown)
- Borehole information (name, static water level, date, operator)
- Test-specific parameters (flowrate, end of pumping, step definitions)
- Run Analysis button

**Main panel tabs**

| Tab | Contents |
|---|---|
| Introduction | Usage instructions, CSV format requirements, method references |
| Data Preview | Raw water level scatter plot and full data table |
| Analysis | Fit plot with adjustable fit window, live R² indicator, optional second fit |
| Results | Results summary table and plain-language interpretation |
| Export | Download results CSV, interactive HTML plots, DOCX report |

### Guided workflow

1. Open the **Introduction** tab and review the instructions and CSV format requirements
2. Select the **test type** from the sidebar
3. Enter **borehole information** — at minimum the borehole name and static water level
4. Upload your **CSV data file**
5. For step-drawdown tests, define each step's flowrate and end time using the **Add Step** button
6. Click **Run Analysis**
7. Check the **Data Preview** tab to confirm the data loaded correctly
8. On the **Analysis** tab, adjust the fit window sliders until the fit line passes through the
   straight-line portion of the data — aim for R² > 0.95
9. Optionally enable a **second fit** (constant-rate and recovery) to bracket the interpretation
   or identify boundary effects
10. Review the **Results** tab for the summary table and plain-language interpretation
11. Download the **DOCX report** from the Export tab

### CSV data format

All test types require a comma-separated `.csv` file with the following two columns:

| Column | Description | Units |
|---|---|---|
| `time_min` | Elapsed time since start of test | minutes |
| `level_m` | Water level measured from datum | m below datum (mbd) |

The datum is typically the top of the casing. Water level values increase (deepen) during pumping
and decrease (recover) during the recovery phase. Template files are available in the `templates/`
folder.

### Fit quality indicator

The R² badge on the Analysis tab uses a traffic-light scheme to guide fit window selection:

| Badge | R² range | Interpretation |
|---|---|---|
| 🟢 Green | ≥ 0.95 | Good — result is reliable |
| 🟡 Amber | 0.85 – 0.95 | Acceptable — treat result with caution |
| 🔴 Red | < 0.85 | Poor — adjust the fit window or review data quality |

### Dual fit (constant-rate and recovery)

Enabling the **Add second fit** toggle reveals a second pair of fit window sliders. This produces:

- A second fit line on the semi-log plot (displayed in a distinct colour with a dashed style)
- A second transmissivity and yield estimate alongside Fit 1 in the results table
- A comparative note in the interpretation text, including an assessment of divergence between the two fits

This feature is useful when the drawdown curve shows a change in slope suggesting a hydraulic
boundary, when two possible straight-line segments exist, or when you wish to present a conservative
and optimistic yield estimate to a decision-maker.

### Export

| Download | Format | Contents |
|---|---|---|
| Results CSV (coming soon) | `.csv` | All numeric results in tabular form |
| Plots (coming soon) | `.html` | Interactive Plotly figures (zoom, pan, hover) |
| Report | `.docx` | Borehole metadata, results table, interpretation, reference |

The DOCX report is an editable Word document, designed as a technical annex that can be incorporated
directly into field reports or design documents.

---

## CLI

A [Typer](https://typer.tiangolo.com)-based command-line interface is available for batch processing
or scripted workflows.

### Constant-rate test

```bash
python cli.py constant-rate data.csv \
  --static-level 10.5 \
  --flowrate 24.0 \
  --borehole-name BH01 \
  --output preview.html \
  --output semilog.html
```

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

Each `--step` flag accepts a `"flowrate,end_time"` pair (m³/h and minutes). Steps must be provided
in ascending order of flowrate and end time.

### Run from config file

All tests for a borehole can be defined in a single JSON or YAML config file and run together:

```bash
python cli.py run borehole_config.yaml
```

### Plot output

By default all plots open in the browser. To save to files, provide one `--output` path per plot
in order:

```bash
python cli.py constant-rate data.csv \
  --static-level 10.5 --flowrate 24.0 \
  --output preview.html \
  --output semilog.html
```

Supported formats: `.html` (interactive), `.png`, `.svg`, `.pdf` (static export requires `kaleido`).

---

## Running tests

```bash
pytest tests/
```

---

## Analysis methods and references

| Test | Method | Source |
|---|---|---|
| Constant-rate | Cooper-Jacob straight-line approximation | ICRC (2011), Section 5 |
| Recovery | Theis recovery method | ICRC (2011), Section 6 |
| Step-drawdown | Hantush-Bierschenk (1964) | ICRC (2011), Section 4 |

Yield estimates use the empirical relationship from MacDonald et al. (2005): approximately
4,000 litres/day per 1 m²/day of transmissivity.

**Primary reference:**
ICRC (2011). *Technical Review — Practical Guidelines for Test Pumping in Water Wells.*
International Committee of the Red Cross, Geneva.

**Supporting reference:**
MacDonald, A.M., Davies, J., Calow, R.C. & Chilton, J. (2005). *Developing Groundwater: A Guide
for Rural Water Supply.* ITDG Publishing, Rugby.

---

## License

MIT