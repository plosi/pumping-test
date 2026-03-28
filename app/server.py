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
from analysis.interpretation import interpret_constant_rate, interpret_recovery, interpret_step_drawdown
from in_out.report import generate_report


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
            # Read second fit inputs only if the toggle is on
            fit2_start = input.fit2_start() if input.use_fit2() else None
            fit2_end = input.fit2_end() if input.use_fit2() else None

            return run_constant_rate(
                borehole_cfg, cr_cfg,
                input.fit_start(), input.fit_end(),
                fit2_start, fit2_end,
            )
            # f: list[FileInfo] = input.cr_file()
            # if not f:
            #     raise ValueError("Please upload a CSV file.")
            # cr_cfg = ConstantRateConfig(
            #     csv_file=Path(f[0]["datapath"]),
            #     flowrate_m3h=input.cr_flowrate(),
            # )
            # return run_constant_rate(borehole_cfg, cr_cfg, input.fit_start(), input.fit_end())

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

        def _badge(r2: float, label: str) -> ui.Tag:
            colour = "success" if r2 > 0.95 else "warning" if r2 > 0.85 else "danger"
            quality = "Good" if r2 > 0.95 else "Acceptable" if r2 > 0.85 else "Poor — adjust window"
            return ui.div(
                ui.p(label, class_="fw-bold mb-1"),
                ui.tags.span(f"R² = {r2:.3f}", class_=f"badge bg-{colour} fs-6"),
                ui.p(quality, class_="mt-1 text-muted small"),
                class_="mb-2"
            )

        if isinstance(s, ConstantRateSession):
            children = [_badge(s.result.fit.r_squared, "Fit 1")]
            if s.result.fit2 is not None:
                children.append(_badge(s.result.fit2.r_squared, "Fit 2"))
            return ui.div(*children)
        elif isinstance(s, RecoverySession):
            return _badge(s.result.fit.r_squared, "Fit")
        else:
            return _badge(s.result.r_squared, "Fit")

    # ----------------------------
    # Plot / Table renders
    # ----------------------------

    @render.ui
    def preview_plot():
        try:
            s = current_session()
        except Exception as e:
            return ui.p(f"Error: {e}", class_="text-danger")

        if isinstance(s, ConstantRateSession):
            fig = plot_constant_preview(s.test, title=f"Constant-Rate — {s.test.borehole.name}", scale_axis=input.preview_scale_plot())
        elif isinstance(s, RecoverySession):
            fig = plot_recovery_preview(s.test, title=f"Recovery — {s.test.borehole.name}", scale_axis=input.preview_scale_plot())
        else:
            fig = plot_step_preview(s.test, title=f"Step-Drawdown — {s.test.borehole.name}", scale_axis=input.preview_scale_plot())

        return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn"))
    
    @render.ui
    def preview_table():
        try:
            s = current_session()
        except Exception as e:
            return ui.p(f"Error: {e}", class_="text-danger")
        
        df = pd.DataFrame({
            "Time, t [min]": s.test.time_series,
            "Water Level, WL [mbd]": s.test.level_series,
        })
        table = gt.GT(data=df)
        return table

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
        
        if not isinstance(s, StepDrawdownSession):
            return ui.div()
        
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
        
        step_table = None
        if isinstance(s, ConstantRateSession):
            r = s.result
            has_fit2 = r.fit2 is not None

            params = ["Transmissivity", "Estimated Yield", "Pumping Flowrate",
                    "Drawdown per log cycle", "R²"]
            values_fit1 = [
                r.transmissivity_m2day,
                r.estimated_yield_m3day,
                r.flowrate_m3day / 24.0,
                r.fit.drawdown_per_log_cycle,
                r.fit.r_squared,
            ]
            units = ["m²/day", "m³/day", "m³/h", "m", ""]

            data = {"Parameter": params, "Fit 1": values_fit1, "Units": units}

            if has_fit2:
                data["Fit 2"] = [
                    r.transmissivity2_m2day,
                    r.estimated_yield2_m3day,
                    r.flowrate_m3day / 24.0,       # same flowrate for both fits
                    r.fit2.drawdown_per_log_cycle,
                    r.fit2.r_squared,
                ]

            df = pd.DataFrame(data)
            
            table = (gt.GT(data=df)
                    .tab_header(title=f"Constant-Rate Test — {s.test.borehole.name}")
                    .fmt_number(columns="Fit 1", decimals=3)
                    .fmt_units(columns="Units"))

            if has_fit2:
                table = table.fmt_number(columns="Fit 2", decimals=3)        
        elif isinstance(s, RecoverySession):
            r = s.result
            params = ["Transmissivity", "Estimated Yield", "Final Recovery", "Pumping Flowrate", "Drawdown per log cycle", "R²"]
            values_fit = [
                r.transmissivity_m2day,
                r.estimated_yield_m3day,
                r.recovery_pcg,
                r.flowrate_m3day / 24.0,
                r.fit.drawdown_per_log_cycle,
                r.fit.r_squared,
            ]
            units = ["m²/day", "m³/day", "%", "m³/h", "m", ""]
            data = {"Parameter": params, "Fit": values_fit, "Units": units}
            df = pd.DataFrame(data)
            
            table = (
                gt.GT(data=df)
                .tab_header(title=f"Recovery Test — {s.test.borehole.name}")
                .fmt_markdown(columns="Parameter")
                .fmt_number(columns="Fit", decimals=3)
                .fmt_units(columns="Units")
            )
        elif isinstance(s, StepDrawdownSession):
            r = s.result
            params = ["Aquifer Loss Coefficient (B)", "Well Loss Coefficient (C)", "Critical Yield", "Estimated Safe Yield (80% of critical yield)", "R²"]
            values = [r.aquifer_loss_coeff,
                      r.well_loss_coeff,
                      r.critical_yield_m3h,
                      r.critical_yield_m3h * 0.8,
                      r.r_squared]
            units = ["m/(m³/h)", "m/(m³/h)^2", "m³/h", "m³/h", ""]
            data = {"Parameter": params, "Value": values, "Units": units}
            df = pd.DataFrame(data) 
            table = (
                gt.GT(data=df)
                .tab_header(title=f"Step-Drawdown Test — {s.test.borehole.name}")
                .fmt_markdown(columns="Parameter")
                .fmt_number(columns="Value", decimals=4)
                .fmt_units(columns="Units")
            )
            step_df = pd.DataFrame(
                {
                    "Step": [str(sr.step.step_number) for sr in r.step_results],
                    "Q [m³/h]": [f"{sr.step.flowrate_m3h:.2f}" for sr in r.step_results],
                    "Drawdown [m]": [f"{sr.drawdown_m:.3f}" for sr in r.step_results],
                    "s/Q [h/m²]": [f"{sr.specific_drawdown_hm2:.4f}" for sr in r.step_results],
                    "BQ [m]": [f"{sr.linear_loss_m:.3f}" for sr in r.step_results],
                    "CQ² [m]": [f"{sr.nonlinear_loss_m:.3f}" for sr in r.step_results],
                    "Efficiency [%]": [f"{sr.efficiency_pct:.1f}" for sr in r.step_results]
                }
            )
            step_table = (
                gt.GT(data=step_df)
                .tab_header(title=f"Per-Step Results — {s.test.borehole.name}")
            )

        return table, step_table
        # return ui.HTML(table.as_raw_html())

    @render.ui
    def interpretation_text():
        try:
            s = current_session()
        except Exception:
            return ui.p("Run the analysis to see interpretation.", class_="text-muted")
        
        name = s.test.borehole.name
        if isinstance(s, ConstantRateSession):
            text = interpret_constant_rate(s.result, name)
        elif isinstance(s, RecoverySession):
            text = interpret_recovery(s.result, name)
        else:
            text = interpret_step_drawdown(s.result, name)
        
        return ui.div(
            ui.h5("Interpretation"),
            ui.markdown(text),   # renders ** bold ** correctly
            class_="mt-3 p-3 bg-light rounded"
        )

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

    @render.download(filename=lambda: f"{input.borehole_name() or 'report'}_pumping_test.docx")
    async def dl_report():
        try:
            s = current_session()
        except Exception:
            return
        buf = generate_report(s)
        yield buf.read()

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