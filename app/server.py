from shiny import render, reactive, ui, session
from shiny.types import FileInfo
from typing import Optional
import pandas as pd
from pathlib import Path
import great_tables as gt

from runner import (
    run_constant_rate, run_recovery, run_step_drawdown,
    ConstantRateSession, RecoverySession, StepDrawdownSession,
)
from config.schema import BoreholeConfig, ConstantRateConfig, RecoveryConfig, StepDrawdownConfig, StepConfig
from plotting.constant_rate import plot_constant_preview, plot_constant_semilog
from plotting.recovery import plot_recovery_preview, plot_recovery_semilog
from plotting.step_drawdown import plot_step_preview, plot_specific_drawdown, plot_losses_vs_q


def server(input, output, session):

    # ----------------------------
    # Core reactive calcs
    # ----------------------------

    @reactive.Calc
    def current_session():
        """
        Runs on every click of the Run button.
        Returns a Session dataclass or raises ValueError.
        """
        input.run()  # take a dependency on the Run button

        test_type = input.test_type()
        borehole_cfg = BoreholeConfig(
            name=input.borehole_name() or "BH",
            static_level_mbd=input.static_level(),
        )

        if test_type == "constant_rate":
            f: list[FileInfo] = input.cr_file()
            if not f:
                raise ValueError("Please upload a CSV file.")
            cr_cfg = ConstantRateConfig(
                csv_file=Path(f[0]["datapath"]),
                flowrate_m3h=input.cr_flowrate(),
            )
            return run_constant_rate(borehole_cfg, cr_cfg, input.fit_start(), input.fit_end())

        elif test_type == "recovery":
            f: list[FileInfo] = input.r_file()
            if not f:
                raise ValueError("Please upload a CSV file.")
            r_cfg = RecoveryConfig(
                csv_file=Path(f[0]["datapath"]),
                flowrate_m3h=input.r_flowrate(),
                end_of_pumping_min=input.r_end_of_pumping(),
            )
            return run_recovery(borehole_cfg, r_cfg, input.fit_start(), input.fit_end())

        elif test_type == "step_drawdown":
            f: list[FileInfo] = input.sd_file()
            if not f:
                raise ValueError("Please upload a CSV file.")
            steps = _parse_step_inputs(input)
            sd_cfg = StepDrawdownConfig(
                csv_file=Path(f[0]["datapath"]),
                steps_raw=steps,
            )
            return run_step_drawdown(borehole_cfg, sd_cfg)

    # ----------------------------
    # Dynamic UI
    # ----------------------------

    @render.ui
    def step_inputs():
        """Render one row of flowrate + end_time inputs per step."""
        n = input.add_step() + 3  # start with 3 steps minimum
        rows = []
        for i in range(1, n + 1):
            rows.append(
                ui.layout_columns(
                    ui.input_numeric(f"sd_flow_{i}", f"Q{i} [m³/h]", value=5.0, min=0.1),
                    ui.input_numeric(f"sd_end_{i}", f"t{i} [min]", value=i * 120),
                    col_widths=[6, 6],
                )
            )
        return ui.div(*rows)

    @render.ui
    def fit_quality_indicator():
        """Show R² with a colour-coded badge."""
        try:
            s = current_session()
        except Exception:
            return ui.p("Run the analysis to see fit quality.", class_="text-muted")

        if isinstance(s, ConstantRateSession):
            r2 = s.result.fit.r_squared
        elif isinstance(s, RecoverySession):
            r2 = s.result.fit.r_squared
        else:
            r2 = s.result.r_squared

        colour = "success" if r2 > 0.95 else "warning" if r2 > 0.85 else "danger"
        label = "Good" if r2 > 0.95 else "Acceptable" if r2 > 0.85 else "Poor — adjust fit window"
        return ui.div(
            ui.tags.span(f"R² = {r2:.3f}", class_=f"badge bg-{colour} fs-6"),
            ui.p(label, class_="mt-1 text-muted small"),
        )

    # ----------------------------
    # Plot renders
    # ----------------------------

    @render.ui
    def preview_plot():
        try:
            s = current_session()
        except Exception as e:
            return ui.p(f"Error: {e}", class_="text-danger")

        if isinstance(s, ConstantRateSession):
            fig = plot_constant_preview(s.test, title=f"Constant-Rate — {s.test.borehole.name}")
        elif isinstance(s, RecoverySession):
            fig = plot_recovery_preview(s.test, title=f"Recovery — {s.test.borehole.name}")
        else:
            fig = plot_step_preview(s.test, title=f"Step-Drawdown — {s.test.borehole.name}")

        return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    @render.ui
    def analysis_plot():
        try:
            s = current_session()
        except Exception as e:
            return ui.p(f"Error: {e}", class_="text-danger")

        if isinstance(s, ConstantRateSession):
            fig = plot_constant_semilog(s.test, s.result, title=f"Cooper-Jacob — {s.test.borehole.name}")
        elif isinstance(s, RecoverySession):
            fig = plot_recovery_semilog(s.test, s.result, title=f"Theis Recovery — {s.test.borehole.name}")
        else:
            fig = plot_specific_drawdown(s.test, s.result, title=f"Hantush-Bierschenk — {s.test.borehole.name}")

        return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn"))
    
    @render.ui
    def losses_vs_q_plot():
        try:
            s = current_session()
        except Exception as e:
            return ui.p(f"Error: {e}", class_="text-danger")
        
        fig = plot_losses_vs_q(s.result, title=f"Linear and non-linear losses - {s.test.borehole.name}", q_max=s.result.critical_yield_m3h*1.1)
        
        return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    # ----------------------------
    # Results renders
    # ----------------------------

    @render.ui
    def results_table():
        try:
            s = current_session()
        except Exception as e:
            return ui.p(f"Error: {e}", class_="text-danger")
        
        if isinstance(s, ConstantRateSession):
            df = pd.DataFrame(
                {
                    "Parameter": ["Transmissivity", "Estimated Yield", "Pumping Flowrate", "Drawdown per log cycle", "R²"],
                    "Value": [s.result.transmissivity_m2day, s.result.estimated_yield_m3day, s.result.flowrate_m3day / 24.0, s.result.fit.drawdown_per_log_cycle, s.result.fit.r_squared],
                    "Units": ["m²/day", "m³/day", "m³/h", "m", ""]
                }
            )
            step_table = None
            table = (
                gt.GT(data=df)
                .tab_header(title=f"Constant-Rate Test — {s.test.borehole.name}")
                .fmt_markdown(columns="Parameter")
                .fmt_number(columns="Value", decimals=2, rows=[0,1,2,3])
                .fmt_units(columns="Units")
            )
        elif isinstance(s, RecoverySession):
            df = pd.DataFrame(
                {
                    "Parameter": ["Transmissivity", "Estimated Yield", "Final Recovery", "Pumping Flowrate", "Drawdown per log cycle", "R²"],
                    "Value": [s.result.transmissivity_m2day, s.result.estimated_yield_m3day, s.result.recovery_pcg, s.result.flowrate_m3day / 24.0, s.result.fit.drawdown_per_log_cycle, s.result.fit.r_squared],
                    "Units": ["m²/day", "m³/day", "%", "m³/h", "m", ""]
                }
            )
            step_table = None
            table = (
                gt.GT(data=df)
                .tab_header(title=f"Recovery Test — {s.test.borehole.name}")
                .fmt_markdown(columns="Parameter")
                .fmt_number(columns="Value", decimals=2, rows=[0,1,2,3,4])
                .fmt_units(columns="Units")
            )
        elif isinstance(s, StepDrawdownSession):
            df = pd.DataFrame(
                {
                    "Parameter": ["Aquifer Loss Coefficient (B)", "Well Loss Coefficient (C)", "Critical Yield", "Estimated Safe Yield (80% of critical yield)", "R²"],
                    "Value": [s.result.aquifer_loss_coeff, s.result.well_loss_coeff, s.result.critical_yield_m3h, s.result.critical_yield_m3h * 0.8, s.result.r_squared],
                    "Units": ["m/(m³/h)", "m/(m³/h)^2", "m³/h", "m³/h", ""]
                }
            )
            table = (
                gt.GT(data=df)
                .tab_header(title=f"Step-Drawdown Test — {s.test.borehole.name}")
                .fmt_markdown(columns="Parameter")
                .fmt_number(columns="Value", decimals=4)
                .fmt_units(columns="Units")
            )
            step_df = pd.DataFrame(
                {
                    "Step": [str(sr.step.step_number) for sr in s.result.step_results],
                    "Q [m³/h]": [f"{sr.step.flowrate_m3h:.2f}" for sr in s.result.step_results],
                    "Drawdown [m]": [f"{sr.drawdown_m:.3f}" for sr in s.result.step_results],
                    "s/Q [h/m²]": [f"{sr.specific_drawdown_hm2:.4f}" for sr in s.result.step_results],
                    "BQ [m]": [f"{sr.linear_loss_m:.3f}" for sr in s.result.step_results],
                    "CQ² [m]": [f"{sr.nonlinear_loss_m:.3f}" for sr in s.result.step_results],
                    "Efficiency [%]": [f"{sr.efficiency_pct:.1f}" for sr in s.result.step_results]
                }
            )
            step_table = (
                gt.GT(data=step_df)
                .tab_header(title=f"Per-Step Results — {s.test.borehole.name}")
            )

        return table, step_table

    @render.ui
    def interpretation_text():
        # TODO: wire up reporting/interpretation.py
        return ui.p("Interpretation will appear here.", class_="text-muted")

    # ----------------------------
    # Export handlers
    # ----------------------------

    @render.download(filename="results.csv")
    def dl_csv():
        # TODO: implement
        yield ""

    @render.download(filename="plots.html")
    def dl_plots():
        # TODO: implement
        yield ""

    @render.download(filename="report.pdf")
    def dl_report():
        # TODO: implement
        yield ""

    # ----------------------------
    # Private helpers
    # ----------------------------

    def _parse_step_inputs(input) -> list[StepConfig]:
        n = input.add_step() + 3
        steps = []
        for i in range(1, n + 1):
            steps.append(StepConfig(
                flowrate_m3h=input[f"sd_flow_{i}"](),
                end_time_min=input[f"sd_end_{i}"](),
            ))
        return steps