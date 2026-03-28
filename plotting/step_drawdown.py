
import plotly.graph_objects as go
from plotting.common import COLOURS, apply_default_layout
from models import PumpingTest, StepDrawdownResult
from typing import Optional
import numpy as np


def plot_step_preview(
    test: PumpingTest,
    title: Optional[str] = None,
    scale_axis: Optional[bool] = False
) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=test.time_series,
            y=test.level_series,
            mode="markers",
            name="Water Level",
            marker=dict(color=COLOURS["data"])
        )
    )
    y_min = test.level_series[0] if scale_axis else 0
    fig.update_yaxes(range=[None, y_min], autorange = "max reversed")
    apply_default_layout(
        fig=fig,
        title=title,
        x_label="Elapsed time [min]",
        y_label="Water level [mbd]",
    )
    return fig

def plot_specific_drawdown(
    test: PumpingTest,
    result: StepDrawdownResult,
    title: Optional[str] = None,
) -> go.Figure:
    fig = go.Figure()

    flowrates = []
    sds = []
    for s in result.step_results:
        flowrates.append(s.step.flowrate_m3h)
        sds.append(s.specific_drawdown_hm2)

    fig.add_trace(
        go.Scatter(
            x=flowrates,
            y=sds,
            mode="markers",
            name="Specific Drawdown",
            marker=dict(color=COLOURS["data"])
        )
    )

    # Evaluate fit line over a dense range
    q_line = np.linspace(flowrates[0], flowrates[-1], 200)
    # sd_line = result.well_loss_coeff * q_line + result.aquifer_loss_coeff
    sd_line = np.array([result.specific_drawdown_at(q) for q in q_line])

    fig.add_trace(
        go.Scatter(
            x=q_line,
            y=sd_line,
            mode="lines",
            name=f"Linear fit (R²={result.r_squared:.3f})",
            marker=dict(color=COLOURS["fit"])
        )
    )

    apply_default_layout(
        fig=fig,
        title=title,
        x_label="Yield [m³/h]",
        y_label="s/Q [h/m²]"
    )
    return fig

def plot_losses_vs_q(
    result: StepDrawdownResult,
    title: Optional[str] = None,
    q_max: Optional[float] = None,
) -> go.Figure:
    B = result.aquifer_loss_coeff
    C = result.well_loss_coeff

    q_max = q_max or max(sr.step.flowrate_m3h for sr in result.step_results) * 1.5
    q_range = np.linspace(0, q_max, 300)

    bq = B * q_range
    bq_cq2 = B * q_range + C * q_range ** 2

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=q_range,
            y=bq_cq2,
            mode='lines',
            name='BQ + CQ² (total)',
            line=dict(color=COLOURS["total"])
        )
    )

    fig.add_trace(
        go.Scatter(
            x=q_range,
            y=bq,
            mode='lines',
            name='BQ (linear)',
            line=dict(color=COLOURS["linear"])
        )
    )

    # Critical yield vertical line
    if C > 0:
        fig.add_vline(
            x=result.critical_yield_m3h,
            line_dash="dash",
            line_color=COLOURS["critical"],
            annotation_text=f"Q_crit = {result.critical_yield_m3h:.1f} m³/h",
            annotation_position="top right",
        )

    apply_default_layout(
        fig,
        title=title or "Linear vs Non-linear Head Losses",
        x_label="Yield [m³/h]",
        y_label="Drawdown [m]",
    )
    return fig

"""

def plot_losses(
    test: PumpingTest,
    result: StepDrawdownResult,
    title: Optional[str] = None,
) -> go.Figure:
    pass

def plot_losses_vs_q(
    result: StepDrawdownResult,
    title: Optional[str] = None,
    q_max: Optional[float] = None,  # upper limit for Q axis; defaults to 1.5 * max step Q
) -> go.Figure:
    pass



"""