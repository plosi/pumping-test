import typer
from pathlib import Path
from typing import Annotated, Optional
from rich.console import Console
from rich.table import Table

from in_out.csv_reader import read_constant_rate_csv, read_recovery_csv, read_step_drawdown_csv
from analysis.constant_rate import analyse_constant_rate
from analysis.recovery import analyse_recovery
from analysis.step_drawdown import analyse_step_drawdown
from models import Borehole, Step, ConstantRateResult, RecoveryResult, StepDrawdownResult

from config.loader import load_config_file
from config.validator import validate_config
from config.schema import BoreholeConfig, ConstantRateConfig, RecoveryConfig, StepDrawdownConfig, StepConfig

import plotly.graph_objects as go
from plotting.step_drawdown import plot_step_preview, plot_specific_drawdown, plot_losses_vs_q
from plotting.constant_rate import plot_constant_preview, plot_constant_semilog
from plotting.recovery import plot_recovery_preview, plot_recovery_semilog

HOURS_PER_DAY = 24.0
SAFE_YIELD_FRACTION = 0.8  # Conservative operating threshold: ICRC (2011) recommends
                            # operating below Q_crit to limit well losses

app = typer.Typer(
    name="pumping-test",
    help="Analyse single-well pumping tests on water wells (ICRC 2011 guidelines).",
    no_args_is_help=True,   # shows help if called with no arguments
)
console = Console()

@app.command()
def constant_rate(
    csv_file: Annotated[Path, typer.Argument(help="Path to the CSV data file.")],
    static_level: Annotated[float, typer.Option(help="Static water level [mbd].")],
    flowrate: Annotated[float, typer.Option(help="Average pumping flowrate [m³/h].")],
    borehole_name: Annotated[str, typer.Option(help="Borehole identifier.")] = "BH",
    fit_start: Annotated[int, typer.Option(help="Index of first point to include in fit.")] = None,
    fit_end: Annotated[Optional[int], typer.Option(help="Index of last point (exclusive).")] = None,
):
    """ Analyse a constant-rate pumping test using the Cooper-Jacob method. """
    borehole_cfg = BoreholeConfig(name=borehole_name, static_level_mbd=static_level)
    cr_cfg = ConstantRateConfig(
        csv_file=csv_file,
        flowrate_m3h=flowrate,
        fit_start_idx=fit_start,
        fit_end_idx=fit_end,
    )
    _run_constant_rate(borehole_cfg, cr_cfg)

@app.command()
def recovery(
    csv_file: Annotated[Path, typer.Argument(help="Path to the CSV data file.")],
    static_level: Annotated[float, typer.Option(help="Static water level [mbd].")],
    flowrate: Annotated[float, typer.Option(help="Average pumping flowrate [m³/h].")],
    end_of_pumping: Annotated[float, typer.Option(help="Elapsed time at which pumping stopped and recovery started [min].")],
    borehole_name: Annotated[str, typer.Option(help="Borehole identifier.")] = "BH",
    fit_start: Annotated[int, typer.Option(help="Index of first point to include in fit.")] = None,
    fit_end: Annotated[Optional[int], typer.Option(help="Index of last point (exclusive).")] = None,
):
    """Analyse a recovery test using the Theis recovery method."""
    borehole_cfg = BoreholeConfig(name=borehole_name, static_level_mbd=static_level)
    r_cfg = RecoveryConfig(
        csv_file=csv_file,
        flowrate_m3h=flowrate,
        end_of_pumping_min=end_of_pumping,
        fit_start_idx=fit_start,
        fit_end_idx=fit_end,
    )
    _run_recovery(borehole_cfg, r_cfg)

@app.command()
def step_drawdown(
    csv_file: Annotated[Path, typer.Argument(help="Path to the CSV data file.")],
    static_level: Annotated[float, typer.Option(help="Static water level [mbd].")],
    steps_raw: Annotated[list[str], typer.Option("--step", help="Step as 'flowrate, end_time'.")],
    borehole_name: Annotated[str, typer.Option(help="Borehole identifier.")] = "BH",
):
    """Analyse a step-drawdown test using the Hantush-Bierschenk method."""
    borehole_cfg = BoreholeConfig(name=borehole_name, static_level_mbd=static_level)

    parsed_steps = []
    for i, s in enumerate(steps_raw, start=1):
        parts = s.strip().split(",")
        if len(parts) != 2:
            typer.echo(
                f"Error: Step {i} '{s}' is not in the expected format 'flowrate,end_time'. "
                "Example: --step '4.2,120'",
                err=True
            )
            raise typer.Exit(code=1)
        try:
            flowrate = float(parts[0])
            end_time = float(parts[1])
        except ValueError:
            typer.echo(
                f"Error: Step {i} '{s}' contains non-numeric values. "
                "Both flowrate and end_time must be numbers.",
                err=True
            )
            raise typer.Exit(code=1)
        parsed_steps.append(Step(step_number=i, flowrate_m3h=flowrate, end_time_min=end_time))

    steps_cfg = [
        StepConfig(flowrate_m3h=flowrate, end_time_min=end_time)
        for flowrate, end_time in parsed_steps
    ]
    sd_cfg = StepDrawdownConfig(csv_file=csv_file, steps=steps_cfg)
    
    _run_step_drawdown(borehole_cfg, sd_cfg)

def _run_constant_rate(
    borehole_config: BoreholeConfig,
    cr_config: ConstantRateConfig,
    fit_start: Optional[int] = None,
    fit_end: Optional[int] = None,
    outputs: Annotated[Optional[list[Path]], typer.Option(
        "--output", "-o",
        help="Output path(s) for plots in order: 1) raw preview, 2) analysis chart." \
        "Save plot to file (.html for interactive, .png/.svg for static). " \
        "If omitted, opens in browser."
    )] = None
) -> None:
    """Shared logic for constant-rate analysis — used by both 'constant_rate' and 'run' commands."""
    borehole = Borehole.minimal(
        name=borehole_config.name,
        static_level_mbd=borehole_config.static_level_mbd
    )
    # CLI overrides take priority over config values
    resolved_fit_start = fit_start if fit_start is not None else cr_config.fit_start_idx
    resolved_fit_end = fit_end if fit_end is not None else cr_config.fit_end_idx

    try:
        test = read_constant_rate_csv(
            path=cr_config.csv_file,
            borehole=borehole,
            flowrate_m3h=cr_config.flowrate_m3h,
        )
        result = analyse_constant_rate(
            test,
            fit_start_idx=resolved_fit_start,
            fit_end_idx=resolved_fit_end,
        )
        fig_constant_preview = plot_constant_preview(test, title=f"Constant Rate Test — {test.borehole.name}")
        fig_constant_semilog = plot_constant_semilog(test, result, title=f"Constant Rate, semilog - {test.borehole.name}")
        figures = [fig_constant_preview, fig_constant_semilog]
        deliver_plots(figures, outputs)

    except ValueError as e:
        typer.echo(f"Error (constant-rate): {e}", err=True)
        raise typer.Exit(code=1)

    _display_constant_rate(result, borehole_config.name)

def _display_constant_rate(result: ConstantRateResult, borehole_name: str) -> None:
    """Render constant-rate results as a Rich table."""
    table = Table(title=f"Constant-Rate Test — {borehole_name}", show_header=True)
    table.add_column("Parameter", justify="left")
    table.add_column("Value", justify="right")
    table.add_column("Units", justify="left")
    table.add_row("Transmissivity", f"{result.transmissivity_m2day:.2f}", "m²/day")
    table.add_row("Estimated Yield", f"{result.estimated_yield_m3day:.2f}", "m³/day")
    table.add_row("Pumping Flowrate", f"{result.flowrate_m3day / HOURS_PER_DAY:.2f}", "m³/h")
    table.add_row("Drawdown per log cycle", f"{result.fit.drawdown_per_log_cycle:.2f}", "m")
    table.add_row("R²", f"{result.fit.r_squared:.4f}", "")
    console.print(table)

def _run_recovery(
    borehole_config: BoreholeConfig,
    r_config: RecoveryConfig,
    fit_start: Optional[int] = None,
    fit_end: Optional[int] = None,
    outputs: Annotated[Optional[list[Path]], typer.Option(
        "--output", "-o",
        help="Output path(s) for plots in order: 1) raw preview, 2) analysis chart." \
        "Save plot to file (.html for interactive, .png/.svg for static). " \
        "If omitted, opens in browser."
    )] = None
) -> None:
    """Shared logic for recover analysis — used by both 'recover_rate' and 'run' commands."""
    borehole = Borehole.minimal(
        name=borehole_config.name,
        static_level_mbd=borehole_config.static_level_mbd
    )
    # CLI overrides take priority over config values
    resolved_fit_start = fit_start if fit_start is not None else r_config.fit_start_idx
    resolved_fit_end = fit_end if fit_end is not None else r_config.fit_end_idx

    try:
        test = read_recovery_csv(
            path=r_config.csv_file,
            borehole=borehole,
            end_of_pumping_min=r_config.end_of_pumping_min,
            flowrate_m3h=r_config.flowrate_m3h,
        )
        result = analyse_recovery(
            test,
            fit_start_idx=resolved_fit_start,
            fit_end_idx=resolved_fit_end,
        )
        fig_recovery_preview = plot_recovery_preview(test, title=f"Recovery Test — {test.borehole.name}")
        fig_recovery_semilog = plot_recovery_semilog(test, result, title=f"Recovery, semilog - {test.borehole.name}")
        figures = [fig_recovery_preview, fig_recovery_semilog]
        deliver_plots(figures, outputs)
        
    except ValueError as e:
        typer.echo(f"Error (recovery): {e}", err=True)
        raise typer.Exit(code=1)

    _display_recovery(result, borehole_config.name)

def _display_recovery(result: RecoveryResult, borehole_name: str) -> None:
    """Render recovery results as a Rich table."""
    table = Table(title=f"Recovery Test — {borehole_name}", show_header=True)
    table.add_column("Parameter", justify="left")
    table.add_column("Value", justify="left")
    table.add_column("Units", justify="left")
    table.add_row("Transmissivity", f"{result.transmissivity_m2day:.2f}", "m²/day")
    table.add_row("Estimated Yield", f"{result.estimated_yield_m3day:.2f}", "m³/day")
    table.add_row("Final recovery", f"{result.recovery_pcg:.2f}", "%")
    table.add_row("Pumping Flowrate", f"{result.flowrate_m3day / HOURS_PER_DAY:.2f}", "m³/h")
    table.add_row("Drawdown for 1 log cycle", f"{result.fit.drawdown_per_log_cycle:.2f}", "m")
    table.add_row("R² of Fit", f"{result.fit.r_squared:.4f}", "")
    console.print(table)

def _run_step_drawdown(
    borehole_config: BoreholeConfig,
    sd_config: StepDrawdownConfig,
    outputs: Annotated[Optional[list[Path]], typer.Option(
        "--output", "-o",
        help="Output path(s) for plots in order: 1) raw preview, 2) analysis chart." \
        "Save plot to file (.html for interactive, .png/.svg for static). " \
        "If omitted, opens in browser."
    )] = None
) -> None:
    """Shared logic for step-drawdown analysis — used by both 'step_drawdown' and 'run' commands."""
    borehole = Borehole.minimal(
        name=borehole_config.name,
        static_level_mbd=borehole_config.static_level_mbd
    )
    steps = [
        Step(step_number=i, flowrate_m3h=s.flowrate_m3h, end_time_min=s.end_time_min)
        for i, s in enumerate(sd_config.steps_raw, start=1)
    ]

    try:
        test = read_step_drawdown_csv(
            path=sd_config.csv_file,
            borehole=borehole,
            steps=steps
        )
        result = analyse_step_drawdown(
            test
        )
        fig_step_preview = plot_step_preview(test, title=f"Step-Drawdown — {test.borehole.name}")
        fig_specific_drawdown = plot_specific_drawdown(test, result, title=f"Specific Drawdown - {test.borehole.name}")
        fig_losses_vs_q = plot_losses_vs_q(result, title=f"Linear and non-linear losses - {test.borehole.name}", q_max=result.critical_yield_m3h*1.1)
        figures = [fig_step_preview, fig_specific_drawdown, fig_losses_vs_q]
        deliver_plots(figures, outputs)
        

    except ValueError as e:
        typer.echo(f"Error (step_drawdown): {e}", err=True)
        raise typer.Exit(code=1)

    _display_step_drawdown(result, borehole_config.name)

def _display_step_drawdown(result: StepDrawdownResult, borehole_name: str) -> None:
    """Render step-drawdown results as a Rich table."""
    table = Table(
        title=f"Step-Drawdown Test Analysis for {borehole_name}",
        show_header=True,
    )
    table.add_column("Parameter", justify="left")
    table.add_column("Value", justify="left")
    table.add_column("Units", justify="left")
    table.add_row("Aquifer Loss Coefficient (B)", f"{result.aquifer_loss_coeff:.4f}", "m/(m³/h)")
    table.add_row("Well Loss Coefficient (C)", f"{result.well_loss_coeff:.4f}", "m/(m³/h)^2")
    table.add_row("Critical Yield", f"{result.critical_yield_m3h:.2f}", "m³/h")
    table.add_row("Estimated Safe Yield (80% of critical yield)", f"{result.critical_yield_m3h * SAFE_YIELD_FRACTION:.2f}", "m³/h")
    table.add_row("R² of Fit", f"{result.r_squared:.4f}", "")
    console.print(table)
    
    step_table = Table(title="Per-Step Results", show_header=True)
    step_table.add_column("Step")
    step_table.add_column("Q [m³/h]")
    step_table.add_column("Drawdown [m]")
    step_table.add_column("s/Q [h/m²]")
    step_table.add_column("BQ [m]")
    step_table.add_column("CQ² [m]")
    step_table.add_column("Efficiency [%]")

    for sr in result.step_results:
        step_table.add_row(
            str(sr.step.step_number),
            f"{sr.step.flowrate_m3h:.2f}",
            f"{sr.drawdown_m:.3f}",
            f"{sr.specific_drawdown_hm2:.4f}",
            f"{sr.linear_loss_m:.3f}",
            f"{sr.nonlinear_loss_m:.3f}",
            f"{sr.efficiency_pct:.1f}",
        )
    console.print(step_table)

def deliver_plot(fig: go.Figure, output: Optional[Path] = None) -> None:
    if output is not None:
        output = Path(output)
    
    if output is None:
        fig.show()   # opens browser
    elif output.suffix == ".html":
        fig.write_html(str(output))
        typer.echo(f"Plot saved to {output}")
    elif output.suffix in (".png", ".svg", ".pdf"):
        fig.write_image(str(output))  # requires kaleido: pip install kaleido
        typer.echo(f"Plot saved to {output}")
    else:
        typer.echo(f"Unsupported output format '{output.suffix}'. Use .html, .png, or .svg.", err=True)
        raise typer.Exit(code=1)

def deliver_plots(figures: list[go.Figure], outputs: Optional[list[Path]]) -> None:
    """
    Save or display multiple plots.
    If outputs is None, all figures open in the browser.
    If outputs is provided, it must match the number of figures exactly.
    """
    if outputs is None:
        for fig in figures:
            deliver_plot(fig)
        return

    if len(outputs) != len(figures):
        typer.echo(
            f"Error: {len(figures)} plot(s) produced but "
            f"{len(outputs)} --output path(s) given. "
            f"Provide exactly {len(figures)} --output flag(s).",
            err=True,
        )
        raise typer.Exit(code=1)

    for fig, path in zip(figures, outputs):
        deliver_plot(fig, path)

@app.command()
def run(
    config_file: Annotated[Path, typer.Argument(help="Path to borehole config file (.json or .yaml).")],
    fit_start: Annotated[Optional[int], typer.Option(help="Override fit start index.")] = 1,
    fit_end: Annotated[Optional[int], typer.Option(help="Override fit end index.")] = None,
    flowrate: Annotated[Optional[float], typer.Option(help="Override pumping flowrate [m³/h].")] = None,
):
    """Run all configured tests for a borehole from a config file."""
    try:
        raw = load_config_file(config_file)
        config = validate_config(raw, config_file)
    except (ValueError, FileNotFoundError) as e:
        typer.echo(f"Config error: {e}", err=True)
        raise typer.Exit(code=1)

    # Apply CLI overrides
    if flowrate is not None:
        if config.constant_rate:
            config.constant_rate.flowrate_m3h = flowrate
        if config.recovery:
            config.recovery.flowrate_m3h = flowrate

    console.print(f"\n[bold]Running tests for borehole: {config.borehole.name}[/bold]")
    console.print(f"Config: {config_file.resolve()}\n")
    # Run each configured test
    if config.constant_rate:
        _run_constant_rate(config.borehole, config.constant_rate, fit_start, fit_end)
    if config.recovery:
        _run_recovery(config.borehole, config.recovery, fit_start, fit_end)
    if config.step_drawdown:
        _run_step_drawdown(config.borehole, config.step_drawdown)


if __name__ == "__main__":
    app()