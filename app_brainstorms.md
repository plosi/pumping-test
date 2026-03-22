Perfect — that's a clear, well-scoped brief. Analyst-first, office use, guided workflow, exportable results. Let me think through the architecture with you before touching any Shiny code.

---

## The analyst's mental model

An analyst receiving field data from a borehole campaign typically has:

- A folder of CSV files (one per test, possibly multiple tests per borehole)
- A field form with borehole metadata (depth, diameter, static level, GPS)
- A deadline to produce a technical note for an engineer or donor

Their workflow is roughly: *load data → verify it looks right → run the analysis → adjust until the fit is good → document the results*. The app should mirror that sequence exactly and not require them to jump backwards.

---

## Proposed app architecture

Here's how I'd structure it, thinking through the full analyst journey:

### Sidebar — persistent across all steps

```
[ Test type selector        ]
[ File upload               ]
─────────────────────────────
[ Borehole info             ]
  Name, date, operator
  Static level (required)
  Depth, diameter (optional)
  Location, GPS (optional)
─────────────────────────────
[ Step parameters           ]
  (visible only for step test)
  + Add step button
─────────────────────────────
[ Run Analysis button       ]
```

The sidebar is always visible. The analyst fills it in left-to-right, top-to-bottom, and hits Run. No pagination, no wizard steps that hide information.

### Main panel — four tabs

```
┌──────────┬──────────┬──────────┬──────────┐
│   Data   │ Analysis │ Results  │  Export  │
│  Preview │          │ Summary  │          │
└──────────┴──────────┴──────────┴──────────┘
```

**Tab 1 — Data Preview**
Raw scatter plot of level vs time. For step tests, vertical lines marking each step end. A data table below the chart. This tab answers: *"did my data load correctly?"*

**Tab 2 — Analysis**
The fit plot (semilog for constant/recovery, specific drawdown for step). Fit controls (start/end index slider) in a panel to the left of the chart. A live R² indicator that changes colour: green > 0.95, amber > 0.85, red below. A brief contextual note explaining what the user is adjusting and why — one sentence, not a manual.

**Tab 3 — Results Summary**
The full results table. For step tests, the per-step breakdown table. A plain-language interpretation paragraph beneath — something like *"The aquifer has a transmissivity of 12.4 m²/day, consistent with a moderately productive sandstone aquifer. Well efficiency at the recommended operating rate is 78%, suggesting acceptable well construction."* This is what gets copy-pasted into the technical note.

**Tab 4 — Export**
Three download buttons:
- Download results as CSV
- Download plots as HTML (interactive)
- Download report as PDF

The PDF is the deliverable. It should contain: borehole metadata, the analysis plots, the results table, and the interpretation paragraph. Everything an engineer needs to review without opening the app.

---

## The reactive data flow

This maps directly onto your library. Think of the Shiny server as three reactive nodes:

```
[file upload + sidebar inputs]
           ↓
    @reactive.Calc          ← csv_reader → PumpingTest
    pumping_test()
           ↓
    @reactive.Calc          ← analyse_*() → Result
    analysis_result()       (depends on fit_start, fit_end sliders)
           ↓
    renders: plots, tables, interpretation text, export files
```

The key insight is that `analysis_result()` depends on the fit sliders — so when the analyst moves a slider, only the fit recalculates, not the data loading. Your `@reactive.Calc` chain means each layer only reruns when its inputs change. This is why building the library as pure functions first was the right call — each `@reactive.Calc` is literally a one-line call into your analysis module.

---

## The interpretation paragraph

This is the feature that will make the app genuinely useful for analysts producing reports. It's not as hard as it sounds — it's a template with conditional logic based on the results:

```python
def interpret_constant_rate(result: ConstantRateResult) -> str:
    T = result.transmissivity_m2day
    if T < 1:
        productivity = "low productivity, likely suitable only for hand pumps"
    elif T < 10:
        productivity = "moderate productivity, suitable for community supply"
    else:
        productivity = "high productivity, suitable for mechanised supply"
    
    fit_quality = "good" if result.fit.r_squared > 0.95 else "acceptable" if result.fit.r_squared > 0.85 else "poor — consider adjusting the fit window"
    
    return (
        f"The Cooper-Jacob analysis yields a transmissivity of {T:.1f} m²/day, "
        f"indicating {productivity} (MacDonald et al., 2005). "
        f"The estimated sustainable yield is {result.estimated_yield_m3day:.0f} m³/day. "
        f"The quality of the straight-line fit is {fit_quality} (R² = {result.fit.r_squared:.3f})."
    )
```

This is deterministic logic — no AI needed, just domain knowledge encoded as conditionals. It belongs in a new module: `reporting/interpretation.py`.

---

## What to build and in what order

**Phase 1 — Constant-rate test, full workflow**
Sidebar → data preview → fit adjustment → results → CSV export. Get this working end-to-end before touching the other test types.

**Phase 2 — Add recovery and step-drawdown**
The scaffold is identical, you're just swapping the reader, analyser, and plots.

**Phase 3 — Interpretation text**
Add `reporting/interpretation.py` and wire it into the Results Summary tab.

**Phase 4 — PDF export**
This is the most technically involved piece. Use `reportlab` or `weasyprint`. Leave it last so it doesn't block everything else.

---

## One structural decision to make now

Your `_run_*` functions in `cli.py` already orchestrate the full workflow for each test type. The Shiny server will need similar orchestration. You have two options:

**Option A** — Let the Shiny server call your library functions directly, same as the CLI does.

**Option B** — Extract a shared `session.py` or `runner.py` module that both the CLI and the Shiny server call into, so the orchestration logic isn't duplicated.

For your current scope Option A is fine — the Shiny server functions will be short enough that duplication isn't a real problem. Option B becomes worth it if you later add a REST API or a third interface.

---

## Before you write `app.py` — one concrete question

Look at your `PumpingTest` properties and your three `analyse_*` functions. The Shiny app's entire server is essentially:

```python
@reactive.Calc
def pumping_test():
    # calls csv_reader based on test type and sidebar inputs
    ...

@reactive.Calc  
def result():
    # calls analyse_* based on test type and fit sliders
    ...
```

Before writing any UI, write those two reactive calcs on paper — what inputs do they depend on, what do they return, and what happens if the file hasn't been uploaded yet? If you can answer that clearly, the rest of the server almost writes itself.

When you're ready, start with the `app_ui` for the constant-rate workflow and paste it here — we'll review the structure before wiring up the server.